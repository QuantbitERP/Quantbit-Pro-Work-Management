import frappe
from frappe.utils import getdate, nowdate, add_days

def check_document_expiry_notifications():
    
    today = getdate(nowdate())
    documents = frappe.get_all(
        "Document Application",
        filters={
            "status": ["in", ["Active", "Issued"]]
        },
        fields=[
            "name",
            "expiry_date",
            "new_expiry_date",
            "extended_date",
            "transaction_type",
            "document_type",
            "applicant"
        ]
    )
    for doc in documents:
        expiry_date = get_effective_expiry_date(doc)
        if not expiry_date:
            continue
        expiry_date = getdate(expiry_date)
        if expiry_date < today:
            mark_document_expired(doc.name)
            send_expired_notification(doc, expiry_date)
            continue
        doc_type = frappe.get_doc("Document Type", doc.document_type)
        if not doc_type.reminder_days_before_expiry:
            continue
        reminder_date = add_days(
            expiry_date,
            -doc_type.reminder_days_before_expiry
        )
        if reminder_date == today:
            send_expiry_reminder(doc, expiry_date)

def get_effective_expiry_date(doc):
    if doc.transaction_type == "Renewal":
        return doc.new_expiry_date
    elif doc.transaction_type == "Extension":
        return doc.extended_date
    else:
        return doc.expiry_date

def mark_document_expired(docname):
    document = frappe.get_doc("Document Application", docname)
    if document.status != "Expired":
        document.status = "Expired"
        document.save(ignore_permissions=True)

def send_expiry_reminder(doc, expiry_date):
    frappe.sendmail(
        recipients=[frappe.session.user], 
        subject="Document Expiry Reminder",
        message=f"""
        <b>Reminder:</b><br><br>
        Document: {doc.name}<br>
        Applicant: {doc.applicant}<br>
        Expiry Date: {expiry_date}<br><br>
        Please initiate renewal or extension process.
        """
    )

def send_expired_notification(doc, expiry_date):

    frappe.sendmail(
        recipients=[frappe.session.user],  
        subject="Document Expired",
        message=f"""
        <b>Alert:</b><br><br>
        Document: {doc.name}<br>
        Applicant: {doc.applicant}<br>
        Expired On: {expiry_date}<br><br>
        Immediate action required.
        """
    )
