import json
import requests
import datetime
from bs4 import BeautifulSoup
from datetime import date, timezone, datetime, timedelta
import frappe
import json
from frappe import _
from erpnext.stock.get_item_details import _get_item_tax_template
from decimal import Decimal
from six import string_types
from frappe.utils.password import get_decrypted_password
from frappe.utils.data import get_link_to_form, add_to_date, now_datetime, time_diff_in_seconds
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def update_queue(docnames, status="On Queue"):
    if isinstance(docnames, str):
        docnames = json.loads(docnames)
    for doc in docnames:
        frappe.db.set_value("Sales Invoice", doc,
                            "e_invoice_process_status", status)
    frappe.db.commit()


@frappe.whitelist()
def login(new_auth_key=False):
    token = frappe.db.get_value(
        "Custom E Invoice Settings", "Custom E Invoice Settings", "auth_token")
    enable = frappe.db.get_single_value('Custom E Invoice Settings', 'enable')
    if not enable:
        frappe.throw(_("Enable {0}.").format(get_link_to_form(
            "Custom E Invoice Settings", "Custom E Invoice Settings")))

    if not new_auth_key:
        exp_time = frappe.db.get_single_value(
            'Custom E Invoice Settings', 'token_expiry')
        if exp_time:
            if time_diff_in_seconds(exp_time, now_datetime()) < 150.0:
                login(True)
        if not token:
            login(True)
        return token

    client_id = frappe.db.get_single_value(
        'Custom E Invoice Settings', 'client_id')
    client_secret = get_decrypted_password('Custom E Invoice Settings', 'Custom E Invoice Settings',
                                           fieldname='client_secret', raise_exception=False)

    if not client_id and client_secret:
        frappe.throw(_("Kindly provide client credentials in {} .").
                     format(get_link_to_form("Custom E Invoice Settings", "Custom E Invoice Settings")))
    # Get auth token
    # prepod
    # url = "https://id.preprod.eta.gov.eg/connect/token"
    # pod
    url = "https://id.eta.gov.eg/connect/token"
    payload = f'grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}&scope=InvoicingAPI'
    headers = {
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        response = requests.request(
            "POST", url, headers=headers, data=payload, verify=False)
        if response.status_code in [200, 202]:
            res = response.json()
            token = res['access_token']
            frappe.db.set_value("Custom E Invoice Settings",
                                None, "auth_token", res['access_token'])
            frappe.db.set_value("Custom E Invoice Settings", None, "token_expiry", add_to_date(
                None, seconds=res.get('expires_in')))
            frappe.db.commit()
            if not token:
                login(True)
            return token
        else:
            frappe.throw(_(f"{response.status_code} {response.text}"))
            return
    except:
        frappe.throw(_("Unable to fetch auth token. Please try again later."))


@frappe.whitelist()
def validate_einvoice(docnames, e_invoice_log=''):

    frappe.db.set_value("E Invoice Log", e_invoice_log, "status", "Started")
    frappe.db.commit()

    if e_invoice_log:
        log_doc = frappe.get_doc("E Invoice Log", e_invoice_log)
    try:
        doc_list = json.loads(docnames)
        doc_list_copy = doc_list[::]
        failed_records = []

        # Loop over selected invoice list
        for doc in doc_list:
            doc_list_copy.remove(doc)
            si_ei_status = "Started"
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()
            response = None
            is_found = False

            # Fetch individual invoice document
            sales_invoice = frappe.get_doc('Sales Invoice', doc)
            uuid = sales_invoice.uuid
            suuid = sales_invoice.submission_id

            # Get auth token
            token = login()

            # Make request
            # prod
            # url = "https://api.invoicing.eta.gov.eg/api/v1.0/documents/recent"
            # url = "https://api.invoicing.eta.gov.eg/api/v1.0/documentSubmissions/" + suuid + '?PageSize=1'
            if e_invoice_log:
                log_invoices = log_doc.invoices

            if not suuid and e_invoice_log:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                            row.response = "Submission ID Not Found"
                            row.execution_time = frappe.utils.now()
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    log_doc.reload()
                    frappe.db.set_value(
                        "Sales Invoice", doc, "e_invoice_process_status", si_ei_status)
                    frappe.db.commit()
                    continue

            url = "https://api.invoicing.eta.gov.eg/api/v1.0/documentSubmissions/" + \
                suuid + '?PageSize=1'

            payload = {}
            headers = {
                'PageSize': '10',
                'PageNo': '1',
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            }
            response = requests.request(
                "GET", url, headers=headers, data=payload, verify=False)

            if e_invoice_log:

                for row in log_invoices:
                    if row.invoice_no == doc:
                        row.response = str(response.json())
                        row.response_code = response.status_code
                        row.headers = str(headers)
                        row.payload = str(payload)
                        row.execution_time = frappe.utils.now()

            if response.status_code == 401:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)

                if e_invoice_log:
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", si_ei_status)
                frappe.db.commit()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", si_ei_status)
                frappe.db.commit()
                continue

            if response.status_code == 400:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                r = response.json()

            if response.status_code in [200, 202]:
                si_ei_status = "Success"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Success"
                            row.under_process = 0
                d = json.loads(response.text)

                if d['overallStatus'] == "Invalid":
                    si_ei_status = "Failed"
                    if e_invoice_log:
                        for row in log_invoices:
                            if row.invoice_no == doc:
                                row.status = si_ei_status
                                row.under_process = 0
                        log_doc.update({
                            'invoices': log_invoices
                        })
                        log_doc.flags.ignore_permissions = True
                        log_doc.flags.ignore_mandatory = True
                        log_doc.save()
                        log_doc.reload()
                        frappe.db.set_value(
                            "Sales Invoice", doc, "e_invoice_process_status", si_ei_status)
                        frappe.db.commit()
                        continue
                    frappe.throw(_("Invoice has status invalid"))
                elif d['overallStatus'] == "Valid":
                    frappe.db.set_value(
                        'Sales Invoice', sales_invoice.name, 'is_valid', 1)
                    frappe.msgprint(
                        msg="Invoice has status valid Please Submit Your Invoice<br>حالة الفاتوره صالحة من فضلك اضغط علي زر <br>submit",
                        indicator='green')
            else:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    log_doc.reload()
                    frappe.db.set_value(
                        "Sales Invoice", doc, "e_invoice_process_status", si_ei_status)
                    frappe.db.commit()
                    continue
                frappe.throw(
                    _(f"Invalid response {response.status_code} - {response.text} "))
            if e_invoice_log:
                log_doc.update({
                    'invoices': log_invoices
                })
                log_doc.flags.ignore_permissions = True
                log_doc.flags.ignore_mandatory = True
                log_doc.save()
                frappe.db.commit()
                log_doc.reload()
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()
    except BaseException as err:
        if e_invoice_log:
            log_doc.update({
                "status": "Error Occured",
                "exception_during_process": (log_doc.exception_during_process or "") + frappe.get_traceback(),
            })
        else:
            frappe.throw(frappe.get_traceback())
    if e_invoice_log:
        for row in log_doc.invoices:
            row.under_process = 0
        log_doc.update({
            "doc_under_process": 0,
            "job_id": ""
        })
        log_doc.flags.ignore_permissions = True
        log_doc.flags.ignore_mandatory = True
        log_doc.save()
        frappe.db.commit()
        log_doc.reload()
    update_queue(doc_list_copy, "Completed")


@frappe.whitelist()
def post_invoice(docnames, e_invoice_log=""):
    frappe.db.set_value("E Invoice Log", e_invoice_log, "status", "Started")
    frappe.db.commit()
    if e_invoice_log:
        log_doc = frappe.get_doc("E Invoice Log", e_invoice_log)
    try:
        doc_list = json.loads(docnames)
        failed_records = []

        # Loop over selected invoice list
        doc_list_copy = doc_list[::]
        for doc in doc_list:
            doc_list_copy.remove(doc)
            si_ei_status = "Started"
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()
            response = None

            # Fetch individual invoice document
            sales_invoice = frappe.get_doc('Sales Invoice', doc)
            items = sales_invoice.items
            ta = sales_invoice.total_amount

            # Get auth token
            token = login()

            # Alter data formats
            uv = []
            for row in items:
                if sales_invoice.currency == "EGP" or sales_invoice.custom_eta_currency == "EGP":
                    uv.append(
                        dict(
                            currencySold="EGP",
                            amountEGP=row.base_rate,
                            amountSold=0,
                            currencyExchangeRate=0,
                        )
                    )
                else:
                    asold = row.rate
                    erate = sales_invoice.conversion_rate
                    uv.append(
                        dict(
                            currencySold=sales_invoice.currency,
                            amountEGP=row.base_rate,
                            amountSold=round(asold, 4),
                            currencyExchangeRate=round(erate, 4),
                        )
                    )
            # uv = [dict(currencySold='EGP', amountEGP=row.rate)for row in items]
            dis = [dict(rate=0, amount=row.discount_before) for row in items]
            taxi = [dict(taxType=row.type, amount=row.tax_amount,
                         subType=row.subtype, rate=row.tax_rate) for row in items]
            taxTotals = [dict(taxType=row.type, amount=row.tax_amount)
                         for row in items]

            for row in sales_invoice.e_invoice_item_wise_tax_details:
                tax_wise_amount = row.tax_wise_amount.split(', ')
                tax_temp_list = row.tax_template.split(', ')
                for temp in tax_temp_list:
                    temp_type = frappe.db.get_value(
                        'Item Tax Template', temp, 'type')
                    tax_rate = frappe.db.get_value(
                        'Item Tax Template', temp, 'rate')
                    subtype = frappe.db.get_value(
                        'Item Tax Template', temp, 'subtype')

                    taxTotals += [dict(taxType=temp_type, amount=float(
                        tax_wise_amount[tax_temp_list.index(temp)]))]
                    taxi += [dict(taxType=temp_type, amount=float(
                        tax_wise_amount[tax_temp_list.index(temp)]), subType=subtype, rate=tax_rate)]

            # Company Data
            id = frappe.db.get_single_value('Custom E Invoice Settings', 'id')
            datemod = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'date_edit')
            date = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'date')
            timemod = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'time')
            name = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'name1')
            actcode = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'activity_code')
            ci = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'region_city')
            st = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'street')
            bn = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'building_number')

            aggregated_data = {}
            for dictionary in taxTotals:
                key = (dictionary['taxType'])
                aggregated_data[key] = aggregated_data.get(
                    key, 0) + dictionary['amount']
                taxt = [{'taxType': key, 'amount': round(
                    value, 2)} for key, value in aggregated_data.items()]
            invoiceLines = []
            for row in items:
                soup = BeautifulSoup(row.description)
                # invoiceLines.append(dict(description=soup.get_text(), itemType=row.item_type, itemCode=row.code, unitType=row.tax_uom if row.tax_uom else row.uom, quantity=row.qty, internalCode=row.item_code, salesTotal=(row.price_list_rate * row.qty) if row.discount_amount else row.base_amount, total=row.total_amount, valueDifference=0,
                #                          totalTaxableFees=0, netTotal=row.base_amount if sales_invoice.discount_amount else row.base_net_amount, itemsDiscount=row.discount_after))
                invoiceLines.append(dict(description=soup.get_text(), itemType=row.item_type, itemCode=row.code, unitType=row.tax_uom if row.tax_uom else row.uom, quantity=row.qty, internalCode=row.item_code, salesTotal=row.base_amount, total=row.total_amount, valueDifference=0,
                                         totalTaxableFees=0, netTotal=row.base_amount if sales_invoice.discount_amount else row.base_net_amount, itemsDiscount=row.discount_after))
            for i in range(len(invoiceLines)):
                invoiceLines[i]['unitValue'] = uv[i]
                invoiceLines[i]['discount'] = dis[i]
                invoiceLines[i]['taxableItems'] = [taxi[i]]
            # Posting Time Set
            postt = sales_invoice.posting_time
            times = str(postt).split(".")[0]
            timeformat = datetime.strptime(times, '%H:%M:%S').time()
            timee = datetime.combine(
                date.today(), timeformat) - timedelta(hours=3)
            time = timee.strftime('%H:%M:%S')
            # Modification Posting Time
            postt = timemod
            times = str(postt).split(".")[0]
            timeformat = datetime.strptime(times, '%H:%M:%S').time()
            timee = datetime.combine(
                date.today(), timeformat) - timedelta(hours=3)
            timemodi = timee.strftime('%H:%M:%S')

    # Make request
            # prepod
            # url = "https://api.preprod.invoicing.eta.gov.eg/api/v1/documentsubmissions"
            # Pod
            url = "https://api.invoicing.eta.gov.eg/api/v1/documentsubmissions"
            payload = json.dumps({
                "issuer": {
                    "address": {
                        "branchID": "0",
                        "country": 'EG',
                        "governate": "Egypt",
                        "regionCity": ci,
                        "street": st,
                        "buildingNumber": bn,
                        "postalCode": "",
                        "floor": "",
                        "room": "",
                        "landmark": "",
                        "additionalInformation": ""
                    },
                    "type": "B",
                    "id": id,
                            "name": name
                },
                "receiver": {
                    "address": {
                        "country": sales_invoice.country_code,
                        "governate": sales_invoice.country,
                        "regionCity": sales_invoice.region_city,
                        "street": sales_invoice.street,
                        "buildingNumber": sales_invoice.building_number,
                        "postalCode": "",
                        "floor": "",
                        "room": "",
                                "landmark": "",
                                "additionalInformation": ""
                    },
                    "type": sales_invoice.customer_types,
                    "id": sales_invoice.tn_id if sales_invoice.customer_types in ['B', 'F'] or sales_invoice.total_amount > 50000 else "",
                    "name": sales_invoice.invoiced_name if sales_invoice.invoiced_name else sales_invoice.customer_name
                },
                "documentType": "I",
                "documentTypeVersion": "1.0",
                "dateTimeIssued": f'{date.strftime("%Y-%m-%d")}T{timemodi}'+'Z' if datemod else f'{sales_invoice.posting_date.strftime("%Y-%m-%d")}T{time}'+'Z',
                "taxpayerActivityCode": actcode,
                "internalID": sales_invoice.name,
                "purchaseOrderReference": sales_invoice.po_no if sales_invoice.po_no else "",
                "purchaseOrderDescription": "",
                "salesOrderReference": "",
                "salesOrderDescription": "",
                "proformaInvoiceNumber": "",
                "payment": {
                    "bankName": sales_invoice.bank if sales_invoice.bank else "",
                    "bankAddress": "",
                    "bankAccountNo": sales_invoice.bank_account_no if sales_invoice.bank_account_no else "",
                    "bankAccountIBAN": sales_invoice.iban if sales_invoice.iban else "",
                    "swiftCode": sales_invoice.swift_number if sales_invoice.swift_number else "",
                    "terms": sales_invoice.p_terms if sales_invoice.p_terms else ""
                },
                "delivery": {
                    "approach": "",
                    "packaging": "",
                    "dateValidity": "2020-09-28T09:30:10Z",
                    "exportPort": "",
                    "grossWeight": 0,
                    "netWeight": 0,
                    "terms": "SomeValue"
                },
                "invoiceLines": invoiceLines,
                "totalDiscountAmount": sales_invoice.total_discount,
                "totalSalesAmount": sales_invoice.base_total + sales_invoice.total_discount if sales_invoice.total_discount else sales_invoice.base_total,
                "netAmount": sales_invoice.base_total if sales_invoice.discount_amount else sales_invoice.base_net_total,
                "taxTotals": taxt,
                "totalAmount": sales_invoice.total_amount,
                "extraDiscountAmount": sales_invoice.discount_amount,
                "totalItemsDiscountAmount": sales_invoice.total_item_discount
            }, ensure_ascii=False)
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
                'Cookie': '75fd0698a2e84d6b8a3cb94ae54530f3=2fd4e7f420b50a2fb3425fb10dfd26f6'
            }
            try:
                payload = get_signatured_data(payload, doc, headers)
                if not payload:
                    if e_invoice_log:
                        log_invoices = log_doc.invoices
                        for row in log_invoices:
                            if row.invoice_no == doc:
                                row.headers = str(headers)
                                row.payload = str(payload)
                                row.execution_time = frappe.utils.now()
                                row.status = "Failed"
                                row.response_code = ""
                                row.under_process = 0
                        log_doc.update({
                            'invoices': log_invoices,
                            "status": "Error Occured",
                            "exception_during_process": (log_doc.exception_during_process or "") + f"{doc}: Payload is empty<br>",
                        })
                        log_doc.flags.ignore_permissions = True
                        log_doc.flags.ignore_mandatory = True
                        log_doc.save()
                        frappe.db.commit()
                        log_doc.reload()
                    frappe.msgprint(msg='Noe Token Response : ' "%s" "<br>Error: %s" % (
                        payload, "Payload is empty from signature function"), indicator='red')

                    continue
                payload = json.loads(payload)
                payload = json.dumps(payload, ensure_ascii=False)
            except BaseException as e:
                if e_invoice_log:
                    log_invoices = log_doc.invoices
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.headers = str(headers)
                            row.payload = str(payload)
                            row.execution_time = frappe.utils.now()
                            row.status = "Failed"
                            row.under_process = 0
                    log_doc.update({
                        'invoices': log_invoices,
                        "status": "Error Occured",
                        "exception_during_process": (log_doc.exception_during_process or "") + (doc or "") + ": " + frappe.get_traceback(),
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", "Failed")
                frappe.db.commit()
                continue
            try:
                response = requests.request(
                    "POST", url, headers=headers, data=payload.encode('utf-8'), verify=False)
                if e_invoice_log:
                    log_invoices = log_doc.invoices
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.response = str(response.json()) if response.status_code not in [
                                401, 404] else str(response)
                            row.response_code = response.status_code
                            row.headers = str(headers)
                            row.payload = str(payload)
                            row.execution_time = frappe.utils.now()

            except:
                if e_invoice_log:
                    log_doc.update({
                        "exception_during_process": (log_doc.exception_during_process or "") + (doc or "") + ": " + frappe.get_traceback()
                    })
                    log_invoices = log_doc.invoices
                    si_ei_status = "Failed"
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = si_ei_status
                            row.response = str(response)
                            row.response_code = response.status_code
                            row.headers = str(headers)
                            row.payload = str(payload)
                            row.execution_time = frappe.utils.now()
                failed_records.append(doc)
                frappe.log_error(message=frappe.get_traceback(
                ), title=f'Invoice document submission [{doc}] - Error')
                if e_invoice_log:
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", "Failed")
                frappe.db.commit()
                continue
            # frappe.errprint(str(type(response)))
            # frappe.errprint(reponse)
            rd = response.json()
            if response.status_code in [404, 401]:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                frappe.log_error(message='Not accepted "%s' % (
                    rd), title=f'Invoice document submission [{doc}] - Identical Error')
                frappe.msgprint(msg='Invoice Not Sent to Egyption Tax Author For Reason : "%s" <br>Check error log for more information' % (rd.get('error')),
                                indicator='red')
                if e_invoice_log:
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", si_ei_status)
                frappe.db.commit()
                continue
            rd = response.json()
            if response.status_code in [200, 202] and not rd['rejectedDocuments'] and rd['acceptedDocuments'][0]['uuid']:
                si_ei_status = "Success"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Success"
                            row.under_process = 0
                uuid = rd['acceptedDocuments'][0]['uuid']
                suuid = rd['submissionId']
                frappe.db.set_value(
                    'Sales Invoice', sales_invoice.name, 'uuid', uuid)
                frappe.db.set_value(
                    'Sales Invoice', sales_invoice.name, 'submission_id', suuid)

            elif response.status_code in [200, 202] and rd['rejectedDocuments'] and not rd['submissionId']:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                # frappe.errprint(rd['rejectedDocuments'][0]['error']['details'])
                errordetail = rd['rejectedDocuments'][0]['error']['details']
                failed_records.append(doc)
                frappe.log_error(message='Not accepted "%s' % (
                    rd), title=f'Invoice document submission [{doc}] - Authentication Error')
                frappe.msgprint(msg='Invoice Not Sent to Egyption Tax Author For Reason : "%s" Check error log for more information' % (errordetail),
                                indicator='red')
            elif response.status_code == 422:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                frappe.log_error(message='Not accepted "%s' % (
                    rd), title=f'Invoice document submission [{doc}] - Identical Error')
                frappe.msgprint(msg='Invoice Not Sent to Egyption Tax Author For Reason : "%s" <br>Check error log for more information' % (rd.get('error')),
                                indicator='red')
            else:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
            if not failed_records:
                frappe.log_error(message=f'{response.status_code} {response.text} \n Recent Payload: {payload} \n Header: {headers}',
                                 title=f'Envoice Successfully Sent to Egyption Tax Authority. [{doc}]')
                frappe.msgprint(msg='Invoice # "%s" Successfully Sent to Egyption Tax Authority.<br>تم أرسال الفاتوره بنجاج من فضلك تاكد من صلاحية الفاتوره بالضغط علي <br>"validate Invoice"<br> UUID is : ' % (sales_invoice.name),
                                indicator='green')
                # frappe.errprint(f"status code: {response.status_code}\nResponse: {response.json()}")
            if e_invoice_log:
                log_doc.update({
                    'invoices': log_invoices
                })
                log_doc.flags.ignore_permissions = True
                log_doc.flags.ignore_mandatory = True
                log_doc.save()
                frappe.db.commit()
                log_doc.reload()
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()

    except BaseException as err:
        if e_invoice_log:
            log_doc.update({
                "status": "Error Occured",
                "exception_during_process": (log_doc.exception_during_process or "") + frappe.get_traceback(),
            })
    if e_invoice_log:
        for row in log_doc.invoices:
            row.under_process = 0
        log_doc.update({
            "doc_under_process": 0,
            "job_id": ""
        })
        log_doc.flags.ignore_permissions = True
        log_doc.flags.ignore_mandatory = True
        log_doc.save()
        frappe.db.commit()
        log_doc.reload()
    update_queue(doc_list_copy, "Completed")


@frappe.whitelist()
def credit_note(docnames, e_invoice_log=''):
    frappe.db.set_value("E Invoice Log", e_invoice_log, "status", "Started")
    frappe.db.commit()
    if e_invoice_log:
        log_doc = frappe.get_doc("E Invoice Log", e_invoice_log)

    try:
        doc_list = json.loads(docnames)

        failed_records = []

        # Loop over selected invoice list
        doc_list_copy = doc_list[::]
        for doc in doc_list:
            doc_list_copy.remove(doc)
            si_ei_status = "Started"
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()
            response = None

            # Fetch individual invoice document
            sales_invoice = frappe.get_doc('Sales Invoice', doc)
            items = sales_invoice.items

            # Get auth token
            token = login()

            # Alter data formats
            uv = []
            for row in items:
                if sales_invoice.currency == "EGP" or sales_invoice.custom_eta_currency == "EGP":
                    uv.append(
                        dict(
                            currencySold="EGP",
                            amountEGP=row.base_rate,
                            amountSold=0,
                            currencyExchangeRate=0,
                        )
                    )
                else:
                    asold = row.rate
                    erate = sales_invoice.conversion_rate
                    uv.append(
                        dict(
                            currencySold=sales_invoice.currency,
                            amountEGP=row.base_rate,
                            amountSold=round(asold, 4),
                            currencyExchangeRate=round(erate, 4),
                        )
                    )
            dis = [dict(rate=0, amount=row.discount_before) for row in items]
            taxi = [dict(taxType=row.type, amount=-(row.tax_amount),
                         subType=row.subtype, rate=row.tax_rate) for row in items]
            taxTotals = [dict(taxType=row.type, amount=-(round(row.tax_amount, 2)))
                         for row in items]

            for row in sales_invoice.e_invoice_item_wise_tax_details:
                tax_wise_amount = row.tax_wise_amount.split(', ')
                tax_temp_list = row.tax_template.split(', ')
                for temp in tax_temp_list:
                    temp_type = frappe.db.get_value(
                        'Item Tax Template', temp, 'type')
                    tax_rate = frappe.db.get_value(
                        'Item Tax Template', temp, 'rate')
                    subtype = frappe.db.get_value(
                        'Item Tax Template', temp, 'subtype')

                    taxTotals += [dict(taxType=temp_type, amount=float(
                        tax_wise_amount[tax_temp_list.index(temp)]))]
                    taxi += [dict(taxType=temp_type, amount=float(
                        tax_wise_amount[tax_temp_list.index(temp)]), subType=subtype, rate=tax_rate)]

            # Company Data
            id = frappe.db.get_single_value('Custom E Invoice Settings', 'id')
            datemod = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'date_edit')
            date = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'date')
            timemod = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'time')
            name = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'name1')
            actcode = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'activity_code')
            ci = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'region_city')
            st = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'street')
            bn = frappe.db.get_single_value(
                'Custom E Invoice Settings', 'building_number')
            aggregated_data = {}
            for dictionary in taxTotals:
                key = (dictionary['taxType'])
                aggregated_data[key] = aggregated_data.get(
                    key, 0) + dictionary['amount']
                taxt = [{'taxType': key, 'amount': round(value, 4)}
                        for key, value in aggregated_data.items()]

            invoiceLines = []
            for row in items:
                soup = BeautifulSoup(row.description)
                invoiceLines.append(
                    dict(
                        description=soup.get_text(),
                        itemType=row.item_type,
                        itemCode=row.code,
                        unitType=row.tax_uom,
                        quantity=-(row.qty),
                        internalCode=row.item_code,
                        salesTotal=-(row.base_amount),
                        total=-(row.total_amount),
                        valueDifference=0,
                        totalTaxableFees=0,
                        netTotal=-
                        (row.base_amount) if sales_invoice.discount_amount else -
                        (row.base_net_amount),
                        itemsDiscount=row.discount_after,
                    )
                )

            for i in range(len(invoiceLines)):
                invoiceLines[i]['unitValue'] = uv[i]
                invoiceLines[i]['discount'] = dis[i]
                invoiceLines[i]['taxableItems'] = [taxi[i]]
            # Time Set
            postt = sales_invoice.posting_time
            times = str(postt).split(".")[0]
            timeformat = datetime.strptime(times, '%H:%M:%S').time()
            timee = datetime.combine(
                date.today(), timeformat) - timedelta(hours=3)
            time = timee.strftime('%H:%M:%S')
            # Modification Posting Time
            postt = timemod
            times = str(postt).split(".")[0]
            timeformat = datetime.strptime(times, '%H:%M:%S').time()
            timee = datetime.combine(
                date.today(), timeformat) - timedelta(hours=3)
            timemodi = timee.strftime('%H:%M:%S')
            # Make request
            # pod
            url = "https://api.invoicing.eta.gov.eg/api/v1/documentsubmissions"
            # prepod
            # url = "https://api.preprod.invoicing.eta.gov.eg/api/v1/documentsubmissions"

            payload = json.dumps({
                "issuer": {
                    "address": {
                        "branchID": "0",
                        "country": 'EG',
                        "governate": "Egypt",
                        "regionCity": ci,
                        "street": st,
                        "buildingNumber": bn,
                        "postalCode": "",
                        "floor": "",
                        "room": "",
                        "landmark": "",
                        "additionalInformation": ""
                    },
                    "type": "B",
                    "id": id,
                    "name": name
                },
                "receiver": {
                    "address": {
                        "country": sales_invoice.country_code,
                        "governate": sales_invoice.country,
                        "regionCity": sales_invoice.region_city,
                        "street": sales_invoice.street,
                        "buildingNumber": sales_invoice.building_number,
                        "postalCode": "",
                        "floor": "",
                        "room": "",
                        "landmark": "",
                        "additionalInformation": ""
                    },
                    "type": sales_invoice.customer_types,
                    "id": sales_invoice.tn_id if sales_invoice.tn_id else "",
                    "name": sales_invoice.customer_name
                },
                "documentType": "C",
                "documentTypeVersion": "1.0",
                "dateTimeIssued": f'{date.strftime("%Y-%m-%d")}T{timemodi}'+'Z' if datemod else f'{sales_invoice.posting_date.strftime("%Y-%m-%d")}T{time}'+'Z',
                "taxpayerActivityCode": actcode,
                "internalID": sales_invoice.name,
                "purchaseOrderReference": sales_invoice.po_no if sales_invoice.po_no else "",
                "purchaseOrderDescription": "",
                "salesOrderReference": "",
                "salesOrderDescription": "",
                "proformaInvoiceNumber": "",
                "payment": {
                    "bankName": sales_invoice.bank if sales_invoice.bank else "",
                    "bankAddress": "",
                    "bankAccountNo": sales_invoice.bank_account_no if sales_invoice.bank_account_no else "",
                    "bankAccountIBAN": sales_invoice.iban if sales_invoice.iban else "",
                    "swiftCode": sales_invoice.swift_number if sales_invoice.swift_number else "",
                    "terms": sales_invoice.p_terms if sales_invoice.p_terms else ""
                },
                "delivery": {
                    "approach": "",
                    "packaging": "",
                    "dateValidity": "2020-09-28T09:30:10Z",
                    "exportPort": "",
                    "grossWeight": 0,
                    "netWeight": 0,
                    "terms": "SomeValue"
                },
                "invoiceLines": invoiceLines,
                "totalDiscountAmount": sales_invoice.total_discount,
                "totalSalesAmount": -(sales_invoice.base_total),
                "netAmount": -(sales_invoice.base_net_total),
                "taxTotals": taxt,
                "totalAmount": -(sales_invoice.total_amount),
                "extraDiscountAmount": -(sales_invoice.discount_amount),
                "totalItemsDiscountAmount": sales_invoice.total_item_discount
            }, ensure_ascii=False)
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
                'Cookie': '75fd0698a2e84d6b8a3cb94ae54530f3=2fd4e7f420b50a2fb3425fb10dfd26f6'
            }

            try:
                payload = get_signatured_data(payload, doc, headers)
                if not payload:
                    if e_invoice_log:
                        log_invoices = log_doc.invoices
                        for row in log_invoices:
                            if row.invoice_no == doc:
                                row.headers = str(headers)
                                row.payload = str(payload)
                                row.execution_time = frappe.utils.now()
                                row.status = "Failed"
                                row.response_code = ""
                                row.under_process = 0
                        log_doc.update({
                            'invoices': log_invoices,
                            "status": "Error Occured",
                            "exception_during_process": (log_doc.exception_during_process or "") + f"{doc}: Payload is empty<br>",
                        })
                        log_doc.flags.ignore_permissions = True
                        log_doc.flags.ignore_mandatory = True
                        log_doc.save()
                        frappe.db.commit()
                        log_doc.reload()
                    frappe.msgprint(msg='Noe Token Response : ' "%s" "<br>Error: %s" % (
                        payload, "Payload is empty from signature function"), indicator='red')

                    continue
                payload = json.loads(payload)
                payload = json.dumps(payload, ensure_ascii=False)
            except BaseException as e:
                if e_invoice_log:
                    log_invoices = log_doc.invoices
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.headers = str(headers)
                            row.payload = str(payload)
                            row.execution_time = frappe.utils.now()
                            row.status = "Failed"
                            row.under_process = 0
                    log_doc.update({
                        'invoices': log_invoices,
                        "status": "Error Occured",
                        "exception_during_process": (log_doc.exception_during_process or "") + (doc or "") + ": " + frappe.get_traceback(),
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", "Failed")
                frappe.db.commit()
                continue

            try:
                response = requests.request(
                    "POST", url, headers=headers, data=payload.encode('utf-8'), verify=False)
                if e_invoice_log:
                    log_invoices = log_doc.invoices
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.response = str(response.json()) if response.status_code not in [
                                404, 401] else str(response)
                            row.response_code = response.status_code
                            row.headers = str(headers)
                            row.payload = str(payload)
                            row.execution_time = frappe.utils.now()
            except:
                if e_invoice_log:
                    log_invoices = log_doc.invoices
                    si_ei_status = "Failed"
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = si_ei_status
                            row.response = str(response)
                            row.response_code = response.status_code
                            row.headers = str(headers)
                            row.payload = str(payload)
                            row.execution_time = frappe.utils.now()
                failed_records.append(doc)
                frappe.log_error(message=frappe.get_traceback(
                ), title=f'Invoice document submission [{doc}] - Error')

            if not response:
                continue
            if response.status_code in [404, 401]:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                frappe.log_error(message='No response please relogin.' + " " + token,
                                 title=f'Invoice document submission [{doc}] - Authentication Error')
                if e_invoice_log:
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", si_ei_status)
                frappe.db.commit()
                continue

            rd = response.json()
            if response.status_code == 202 and not rd['rejectedDocuments'] and rd['acceptedDocuments'][0]['uuid']:
                cduuid = rd['acceptedDocuments'][0]['uuid']
                frappe.db.set_value(
                    'Sales Invoice', sales_invoice.name, 'cduuid', rd['acceptedDocuments'][0]['uuid'])
                si_ei_status = "Success"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Success"
                            row.under_process = 0

            elif response.status_code == 400:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                r = response.json()
                failed_records.append(doc)
                frappe.log_error(message='Not accepted "%s' % (
                    r), title=f'Invoice document submission [{doc}] - Authentication Error')

            elif response.status_code in [422, 401, 404]:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                r = response.json()
                failed_records.append(doc)
                frappe.log_error(message='Not accepted "%s' % (
                    r), title=f'Invoice document submission [{doc}] - Authentication Error')
            else:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                frappe.log_error(message='Invoice for "%s" Not not sent to Egyption Tax Authority response code is "%s" Reason "%s" Json "%s"' % (sales_invoice.customer, response.status_code, rd['rejectedDocuments'][0], payload),
                                 title=f'Invoice document submission [{doc}]')

            if e_invoice_log:
                log_doc.update({
                    'invoices': log_invoices
                })
                log_doc.flags.ignore_permissions = True
                log_doc.flags.ignore_mandatory = True
                log_doc.save()
                frappe.db.commit()
                log_doc.reload()
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()

        if not failed_records:
            if response.status_code in [404, 401]:
                frappe.msgprint(
                    msg='Credit Note not Sent to Egyption Tax Authority please pres send again. Response Code : ' "%s" % (
                        response.status_code),
                    indicator='red')
            else:
                frappe.msgprint(
                    msg='Credit Note Successfully Sent to Egyption Tax Authority. Response Code : ' "%s" % (
                        response.status_code),
                    indicator='green')
    except BaseException as err:
        if e_invoice_log:
            log_doc.update({
                "status": "Error Occured",
                "exception_during_process": (log_doc.exception_during_process or "") + frappe.get_traceback(),
            })
    if e_invoice_log:
        for row in log_doc.invoices:
            row.under_process = 0
        log_doc.update({
            "doc_under_process": 0,
            "job_id": ""
        })
        log_doc.flags.ignore_permissions = True
        log_doc.flags.ignore_mandatory = True
        log_doc.save()
        frappe.db.commit()
        log_doc.reload()
    update_queue(doc_list_copy, "Completed")


@frappe.whitelist()
def cancel(docnames, e_invoice_log=''):
    frappe.db.set_value("E Invoice Log", e_invoice_log, "status", "Started")
    frappe.db.commit()
    if e_invoice_log:
        log_doc = frappe.get_doc("E Invoice Log", e_invoice_log)
    try:
        doc_list = json.loads(docnames)

        failed_records = []
        # Loop over selected invoice list
        doc_list_copy = doc_list[::]
        for doc in doc_list:
            doc_list_copy.remove(doc)
            si_ei_status = "Started"
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()
            response = None
            sales_invoice = frappe.get_doc('Sales Invoice', doc)
            uuid = sales_invoice.uuid or ""
            # Get auth token
            token = login()

            # cancel submitted Documents
            url = "https://api.invoicing.eta.gov.eg/api/v1.0/documents/state" + uuid + '/state'

            payload = json.dumps({
                "status": "cancelled",
                "reason": "some reason for cancelled document"
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
                'Cookie': '75fd0698a2e84d6b8a3cb94ae54530f3=eb44eac10ef20d32b2e68814a84fe545'
            }

            response = requests.request(
                "PUT", url, headers=headers, data=payload, verify=False)
            if e_invoice_log:
                log_invoices = log_doc.invoices
                for row in log_invoices:
                    if row.invoice_no == doc:
                        row.response_code = response.status_code
                        row.response = str(response.json()) if response.status_code not in [
                            401, 404] else str(response)

                        row.headers = str(headers)
                        row.payload = str(payload)
                        row.execution_time = frappe.utils.now()
            if response.status_code in [404, 401]:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                if e_invoice_log:
                    log_doc.update({
                        'invoices': log_invoices
                    })
                    log_doc.flags.ignore_permissions = True
                    log_doc.flags.ignore_mandatory = True
                    log_doc.save()
                    frappe.db.commit()
                    log_doc.reload()
                frappe.db.set_value("Sales Invoice", doc,
                                    "e_invoice_process_status", si_ei_status)
                frappe.db.commit()
                continue

            if response.status_code == 400:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
                failed_records.append(doc)
                r = response.json()
                # frappe.log_error(message= 'Envoice Not Cancelled for "%s".' % ((r.get('error').get('details')) if r else r), title=f'Invoice document cancellation [{doc}] - Cancellation Error')
                # frappe.log_error(message= 'Envoice Not Cancelled for "%s".' %( (r.get('error').get('details')) if r else r), title=f'Invoice document cancellation [{doc}] - Cancellation Error')
            elif response.status_code in [200, 202]:
                si_ei_status = "Success"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Success"
                            row.under_process = 0
            else:
                si_ei_status = "Failed"
                if e_invoice_log:
                    for row in log_invoices:
                        if row.invoice_no == doc:
                            row.status = "Failed"
                            row.under_process = 0
            if e_invoice_log:
                log_doc.update({
                    'invoices': log_invoices
                })
                log_doc.flags.ignore_permissions = True
                log_doc.flags.ignore_mandatory = True
                log_doc.save()
                frappe.db.commit()
                log_doc.reload()
            frappe.db.set_value("Sales Invoice", doc,
                                "e_invoice_process_status", si_ei_status)
            frappe.db.commit()
        if not failed_records:
            frappe.msgprint(
                msg='Envoice Successfully Cancelled "%s".' % (
                    response.status_code),
                indicator='green')

        if failed_records:
            frappe.msgprint(
                msg=f'{len(failed_records)} records are failed to cancel. Check error log for more info.',
                indicator='red')
    except BaseException as err:
        if e_invoice_log:
            log_doc.update({
                "status": "Error Occured",
                "exception_during_process": (log_doc.exception_during_process or "") + frappe.get_traceback(),
            })
    if e_invoice_log:
        for row in log_doc.invoices:
            row.under_process = 0
        log_doc.update({
            "doc_under_process": 0,
            "job_id": ""
        })
        log_doc.flags.ignore_permissions = True
        log_doc.flags.ignore_mandatory = True
        log_doc.save()
        frappe.db.commit()
        log_doc.reload()
    update_queue(doc_list_copy, "Completed")


@frappe.whitelist()
def get_default_tax_template_values(filters):
    if isinstance(filters, string_types):
        filters = json.loads(filters)

    item_doc = frappe.get_cached_doc('Item', filters.get('item_type'))
    # frappe.errprint(item_doc)
    item_group = filters.get('item_group')
    taxes = item_doc.taxes or []

    while item_group:
        item_group_doc = frappe.get_cached_doc('Item Group', item_group)
        taxes += item_group_doc.taxes or []
        item_group = item_group_doc.parent_item_group

    if taxes:
        valid_from = filters.get('valid_from')
        valid_from = valid_from[1] if isinstance(
            valid_from, list) else valid_from

        args = {
            'item_code': filters.get('item_code'),
            'posting_date': valid_from,
            'tax_category': filters.get('tax_category'),
            'company': filters.get('company')
        }

        taxes = _get_item_tax_template(args, taxes, for_validate=True)
        item_tax_templates = [(d,) for d in set(taxes)]
        if item_tax_templates[0][0]:
            subtype = frappe.db.get_value(
                'Item Tax Template', {'name': item_tax_templates[0][0]}, 'subtype')
            rate = frappe.db.get_value('Item Tax Template', {
                                       'name': item_tax_templates[0][0]}, 'rate')
            type_field = frappe.db.get_value(
                'Item Tax Template', {'name': item_tax_templates[0][0]}, 'type')
            return [item_tax_templates[0][0], type_field, subtype, rate]


def make_si_custom_fields(update=True):
    custom_fields = {
        "Sales Invoice": [
            {
                "fieldname": "section_break",
                "fieldtype": "Section Break",
                "insert_after": "items",
            },
            {
                "fieldname": "tax_item",
                "label": "Tax Item",
                "fieldtype": "Link",
                "options": "Item",
                "insert_after": "section_break",
            },
            {
                "fieldname": "tax_template",
                "label": "Tax Template",
                "fieldtype": "Table MultiSelect",
                "options": "Multi Tax Template",
                "insert_after": "tax_item",
            },
            {
                "fieldname": "update_tax",
                "label": "Update Tax",
                "fieldtype": "Button",
                "insert_after": "tax_template",
            },
            {
                "fieldname": "custom_tax_listing",
                "label": "Custom Tax Listing",
                "fieldtype": "Table",
                "read_only": 1,
                "options": "Einvoice Custom Taxes Listing",
                "insert_after": "update_tax"
            },
            {
                "fieldname": "e_invoice_item_wise_tax_details",
                "label": "E invoice Item Wise Tax Details",
                "fieldtype": "Table",
                "read_only": 1,
                "options": "E invoice Item Wise Tax Details",
                "insert_after": "custom_tax_listing"
            }
        ]
    }
    create_custom_fields(
        custom_fields, ignore_validate=frappe.flags.in_patch, update=update
    )


def update_tax(doc):
    if isinstance(doc, string_types):
        doc = frappe._dict(json.loads(doc))
    new_tax = {}
    copy_tax = {}
    for item in doc["items"]:
        if item["item_code"] == doc["tax_item"]:
            for template in doc["tax_template"]:
                if template["tax_template"] != item["item_tax_template"]:
                    tax_rate_list = frappe.get_all(
                        "Item Tax Template Detail",
                        {"parent": template["tax_template"]},
                        ["tax_type", "tax_rate"],
                    )

                    for tax_rate in tax_rate_list:
                        new_tax[tax_rate["tax_type"]] = item["amount"] * (
                            tax_rate["tax_rate"] / 100
                        )
                        copy_tax[tax_rate["tax_type"]] = item["amount"] * (
                            tax_rate["tax_rate"] / 100
                        )
            break
    # frappe.errprint(copy_tax)
    if not "custom_tax_listing" in doc:
        doc["custom_tax_listing"] = []

    for tax in doc["custom_tax_listing"]:
        if tax["account_head"] in new_tax:
            if not "tax_amount" in tax:
                tax["tax_amount"] = 0
            tax["tax_amount"] = tax["tax_amount"] + \
                new_tax[tax["account_head"]]
            new_tax.pop(tax["account_head"])

    if new_tax:
        for _tax in new_tax.keys():
            if new_tax[_tax]:
                doc["custom_tax_listing"].append({
                    "tax_amount": new_tax[_tax],
                    "account_head": _tax,
                })

    if not "e_invoice_item_wise_tax_details" in doc:
        doc["e_invoice_item_wise_tax_details"] = []

    found = False
    if doc['e_invoice_item_wise_tax_details']:
        for row in doc['e_invoice_item_wise_tax_details']:
            if row['item'] == doc['tax_item']:
                row['tax_template'] = row['tax_template'] + ', ' + \
                    ', '.join([template["tax_template"]
                              for template in doc["tax_template"]])
                row['amount'] += sum([copy_tax[tax]
                                     for tax in copy_tax.keys()])
                row['tax_wise_amount'] = row['tax_wise_amount'] + ', ' + \
                    ', '.join([str(copy_tax[tax]) for tax in copy_tax.keys()])
                row['account_head'] = row['account_head'] + ', ' + \
                    ', '.join([str(tax) for tax in copy_tax.keys()])
                found = True

    if not found:
        doc['e_invoice_item_wise_tax_details'].append(
            {'item': doc['tax_item'],
                'tax_template': ', '.join([template["tax_template"] for template in doc["tax_template"]]),
                'amount': sum([copy_tax[tax] for tax in copy_tax.keys()]),
             'tax_wise_amount': ', '.join([str(copy_tax[tax]) for tax in copy_tax.keys()]),
             'account_head': ', '.join([str(tax) for tax in copy_tax.keys()])})

    return [doc['custom_tax_listing'], doc['e_invoice_item_wise_tax_details']]


def get_signatured_data(payload, doc, headers):
    try:
        url = frappe.db.get_value(
            "Custom E Invoice Settings", "Custom E Invoice Settings", "electronic_signature_device_endpoint")
        # response = requests.request("POST", f'{url}/SigningService', data = payload, headers = headers, verify = False)
        response = requests.request(
            "POST", f'{url}/SigningService', data=payload.encode('utf-8'), headers=None, verify=False)
        if response.status_code in [200, 202]:
            res = response.json()
            return res
        else:
            frappe.throw(
                _(f"Get Signatured Data API Error - {response.status_code}"))
            return

    except:
        frappe.log_error(message=frappe.get_traceback(),
                         title=f'Get Signatured Data [{doc}] - Error')


def on_submit(doc, action):
    if not doc.is_valid:
        frappe.throw(_("Unable to submit this record. It's not yet validated"))
