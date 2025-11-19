# Copyright (c) 2022, alaabadry1@gmail.com  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from rq.command import send_stop_job_command
from frappe.utils.background_jobs import get_redis_conn
from e_invoice.custom.python.e_invoice_enqueue import post_invoice
from e_invoice.custom.python.e_invoice_enqueue import cancel
from e_invoice.custom.python.e_invoice_enqueue import credit_note
import json

class EInvoiceLog(Document):
	def validate(self):
		if self.cancelling:
			self.cancelling=0
			return
		self.total_count=len(self.invoices)
		self.success_count=len([1 for doc in self.invoices if doc.status=="Success"])
		self.failed_count=len([1 for doc in self.invoices if doc.status=="Failed"])
		response=[
				f'''{indicator(doc.status)}  <b><a href="/app/sales-invoice/{doc.invoice_no}" target="_blank" style="padding-right: 10px;">{doc.invoice_no}</a>Execution Time: {doc.execution_time}</b><br>
				<b style="padding-right: 10px;">Response Code: </b>{doc.response_code} <b>Response: </b>{doc.response}
				'''
				for doc in self.invoices]
		self.response='<br><br>'.join(response)

		if self.success_count and self.success_count!=self.total_count:
			self.status='Partial Success'
		elif self.failed_count and self.failed_count!=self.total_count:
			self.status='Partial Failed'
		elif self.failed_count==self.total_count:
			self.status="All Failed"
		elif self.success_count==self.total_count:
			self.status="All Success"


def indicator(status):
	color={
		'Not Started': 'yellow',
		'Success': 'green',
		'Failed': 'red'
	}
	return f"""
		<span class="indicator-pill whitespace-nowrap {color.get(status)}"><span>{status}</span></span>
		"""


@frappe.whitelist()
def cancel_selected(docname="", docnames=json.dumps([])):
	if isinstance(docnames, str):
		doclist=json.loads(docnames)
	else:
		doclist=docnames
	if not doclist or not frappe.db.exists("E Invoice Log", docname):
		return
	doc=frappe.get_doc("E Invoice Log", docname)
	resend_invoices=[]
	for row in doc.invoices:
		if row.under_process==1 and row.invoice_no not in doclist:
			resend_invoices.append(row.invoice_no)
	cancel_queue(docname)
	if doc.process1=="Einvoice Bulk Send":
		return post_invoice(json.dumps(resend_invoices))
	elif doc.process1=="Einvoice Bulk Cancel":
		return cancel(json.dumps(resend_invoices))
	elif doc.process1=="Einvoice Bulk Credit":
		return credit_note(json.dumps(resend_invoices))


@frappe.whitelist()
def cancel_queue(docname):
	doc=frappe.get_all("RQ Job Ids", {"e_invoice_log": docname}, pluck="job_id")
	if doc:
		try:
			send_stop_job_command(get_redis_conn(), doc[0])
			remove_job_id_from_registry(docname, doc[0])
			doc=frappe.get_doc("E Invoice Log", docname)
			update_queue([row.invoice_no for row in doc.invoices if(frappe.db.get_value("Sales Invoice", row.invoice_no, "e_invoice_process_status") not in ["Success", "Failed"])], "Cancelled")
		except:
			pass
		doc=frappe.get_doc("E Invoice Log", docname)
		for row in doc.invoices:
			row.under_process=0
		doc.status="Cancelled"
		doc.cancelling=1
		doc.doc_under_process=0
		doc.save()
		frappe.db.commit()

def remove_job_id_from_registry(name, job_id):
	doc=frappe.get_all("RQ Job Ids", {"job_id": job_id, "e_invoice_log": name}, pluck="job_id")
	if doc:
		rqdoc=frappe.get_single("RQ Job Registry")
		for row in rqdoc.job_ids:
			if row.job_id==doc[0]:
				rqdoc.job_ids.remove(row)
		rqdoc.save()
		frappe.db.commit()


def update_queue(docnames, status="On Queue"):
    if isinstance(docnames, str):
        docnames=json.loads(docnames)
    for doc in docnames:
        frappe.db.set_value("Sales Invoice", doc, "e_invoice_process_status", status)
