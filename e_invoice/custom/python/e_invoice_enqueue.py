import frappe
from e_invoice.custom.python.sales_invoice import post_invoice as pi
from e_invoice.custom.python.sales_invoice import cancel as pc
from e_invoice.custom.python.sales_invoice import credit_note as pcreidt
from e_invoice.custom.python.sales_invoice import validate_einvoice as pvalidate
import json



def update_queue(docnames, status="On Queue"):
    if isinstance(docnames, str):
        docnames=json.loads(docnames)
    for doc in docnames:
        frappe.db.set_value("Sales Invoice", doc, "e_invoice_process_status", status)


def update_job_id(job_id, name):
    doc=frappe.get_single("RQ Job Registry")
    to_update=True
    for row in doc.job_ids:
        if row.e_invoice_log==name:
            row.job_id=job_id
            to_update=False
    if to_update:
        doc.update({
            "job_ids": (doc.job_ids or []) + [{"e_invoice_log": name, "job_id": job_id}]
        })
    doc.save()
    frappe.db.commit()


@frappe.whitelist()
def post_invoice(docnames, log=None):
    update_queue(docnames)
    doclist=json.loads(docnames)
    process="Einvoice Bulk Send"
    log_docs=frappe.get_all('E Invoice Log', {'process1': process, 'doc_under_process':1}, pluck="name")
    log_doc_invoices=[]
    for doc in log_docs:
        log_doc=frappe.get_doc('E Invoice Log', doc)
        log_doc_invoices += [row.invoice_no for row in log_doc.invoices]
    for doc in doclist:
        check_under_process(log_doc_invoices, doc, process)
    if not log:
        elog=frappe.new_doc("E Invoice Log")
        elog.update({
        "last_execution": frappe.utils.now(),
        "process1": "Einvoice Bulk Send",
        "status": "Not Started",
        "total_count": "",
        "doc_under_process": 1,
        "invoices": [
            {
                "invoice_no": doc,
                "execution_time": frappe.utils.now(),
                "status": "Not Started",
                "under_process": 1,
            }
            for doc in doclist if(check_under_process(log_doc_invoices, doc, process))]

        })
        elog.save(ignore_permissions=True)
    else:
        elog=frappe.get_doc("E Invoice Log", log)
        elog.update({
            "last_execution": frappe.utils.now(),
            "status": "Not Started",
            "doc_under_process": 1,
            "exception_during_process": "",
        })
        for row in elog.invoices:
            if row.invoice_no in doclist:
                row.under_process=1
        elog.save(ignore_permissions=True)
    
    job_id=frappe.enqueue(pi, docnames=docnames, e_invoice_log=elog.name, queue='long')
    job_id=job_id._id
    update_job_id(job_id, elog.name)
    return elog.name
    


@frappe.whitelist()
def cancel(docnames, log=None):
    doclist=json.loads(docnames)
    update_queue(docnames)
    process="Einvoice Bulk Cancel"
    log_docs=frappe.get_all('E Invoice Log', {'process1': process, 'doc_under_process':1}, pluck="name")
    log_doc_invoices=[]
    for doc in log_docs:
        log_doc=frappe.get_doc('E Invoice Log', doc)
        log_doc_invoices += [row.invoice_no for row in log_doc.invoices]
    for doc in doclist:
        check_under_process(log_doc_invoices, doc, process)
    if not log:
        elog=frappe.new_doc("E Invoice Log")
        elog.update({
        "last_execution": frappe.utils.now(),
        "process1": "Einvoice Bulk Cancel",
        "status": "Not Started",
        "total_count": "",
        "doc_under_process": 1,
        "invoices": [
            {
                "invoice_no": doc,
                "execution_time": frappe.utils.now(),
                "status": "Not Started",
                "under_process": 1,
            }
            for doc in doclist if(check_under_process(log_doc_invoices, doc, process))]
        })
        elog.save(ignore_permissions=True)
    else:
        elog=frappe.get_doc("E Invoice Log", log)
        elog.update({
            "last_execution": frappe.utils.now(),
            "status": "Not Started",
            "doc_under_process": 1,
            "exception_during_process": "",
        })
        for row in elog.invoices:
            if row.invoice_no in doclist:
                row.under_process=1
        elog.save(ignore_permissions=True)
        elog.save(ignore_permissions=True)
    
    job_id=frappe.enqueue(pc, docnames=docnames, e_invoice_log=elog.name, queue='long')
    job_id=job_id._id
    update_job_id(job_id, elog.name)
    return elog.name

@frappe.whitelist()
def credit_note(docnames, log=None):
    doclist=json.loads(docnames)
    update_queue(docnames)
    process="Einvoice Bulk Credit"
    log_docs=frappe.get_all('E Invoice Log', {'process1': process, 'doc_under_process':1}, pluck="name")
    log_doc_invoices=[]
    for doc in log_docs:
        log_doc=frappe.get_doc('E Invoice Log', doc)
        log_doc_invoices += [row.invoice_no for row in log_doc.invoices]
    for doc in doclist:
        check_under_process(log_doc_invoices, doc, process)
    if not log:
        elog=frappe.new_doc("E Invoice Log")
        elog.update({
        "last_execution": frappe.utils.now(),
        "process1": "Einvoice Bulk Credit",
        "status": "Not Started",
        "total_count": "",
        "doc_under_process": 1,
        "invoices": [
            {
                "invoice_no": doc,
                "execution_time": frappe.utils.now(),
                "status": "Not Started",
                "under_process": 1,
            }
            for doc in doclist if(check_under_process(log_doc_invoices, doc, process))]

        })
        elog.save(ignore_permissions=True)
    else:
        elog=frappe.get_doc("E Invoice Log", log)
        elog.update({
            "last_execution": frappe.utils.now(),
            "status": "Not Started",
            "doc_under_process": 1,
            "exception_during_process": "",
        })
        for row in elog.invoices:
            if row.invoice_no in doclist:
                row.under_process=1
        elog.save(ignore_permissions=True)
        elog.save(ignore_permissions=True)
    
    job_id=frappe.enqueue(pcreidt, docnames=docnames, e_invoice_log=elog.name, queue='long')
    job_id=job_id._id
    update_job_id(job_id, elog.name)
    return elog.name

def check_under_process(docs, doc, process):
    if(doc in docs):
        frappe.throw(f"{doc} is under process: {process}")
    return True


@frappe.whitelist()
def validate(docnames, log=None):
    doclist = json.loads(docnames)
    update_queue(docnames)
    process = "Einvoice Bulk Validate"
    log_docs = frappe.get_all('E Invoice Log', {'process1': process, 'doc_under_process':1}, pluck="name")
    log_doc_invoices = []

    for doc in log_docs:
        log_doc = frappe.get_doc('E Invoice Log', doc)
        log_doc_invoices += [row.invoice_no for row in log_doc.invoices]

    for doc in doclist:
        check_under_process(log_doc_invoices, doc, process)

    if not log:
        elog = frappe.new_doc("E Invoice Log")

        elog.update({
        "last_execution": frappe.utils.now(),
        "process1": "Einvoice Bulk Validate",
        "status": "Not Started",
        "total_count": "",
        "doc_under_process": 1,
        "invoices": [
            {
                "invoice_no": doc,
                "execution_time": frappe.utils.now(),
                "status": "Not Started",
                "under_process": 1,
            }
            for doc in doclist if(check_under_process(log_doc_invoices, doc, process))]
        })
        elog.save(ignore_permissions = True)

    else:
        elog = frappe.get_doc("E Invoice Log", log)
        elog.update({
            "last_execution": frappe.utils.now(),
            "status": "Not Started",
            "doc_under_process": 1,
            "exception_during_process": "",
        })

        for row in elog.invoices:
            if row.invoice_no in doclist:
                row.under_process = 1

        elog.save(ignore_permissions = True)
        elog.save(ignore_permissions = True)
    
    job_id = frappe.enqueue(pvalidate, docnames = docnames, e_invoice_log = elog.name, queue = 'long')
    job_id = job_id._id
    update_job_id(job_id, elog.name)

    return elog.name