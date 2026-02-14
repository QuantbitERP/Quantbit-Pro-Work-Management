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
            "applicant",
            "owner"
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
        if reminder_date <= today:
            send_expiry_reminder(doc, expiry_date)

def get_effective_expiry_date(doc):
    if doc.transaction_type == "Renewal":
        return doc.new_expiry_date
    elif doc.transaction_type == "Extension":
        return doc.extended_date
    return doc.expiry_date

def mark_document_expired(docname):
    document = frappe.get_doc("Document Application", docname)
    if document.status != "Expired":
        document.status = "Expired"
        document.save(ignore_permissions=True)

def send_expiry_reminder(doc, expiry_date):
    recipient = frappe.db.get_value("User", doc.owner, "email")
    if not recipient:
        return
    frappe.sendmail(
        recipients=[recipient],
        subject="Document Expiry Reminder",
        message=f"""
        <b>Reminder:</b><br><br>
        Document: {doc.name}<br>
        Applicant: {doc.applicant}<br>
        Expiry Date: {expiry_date}<br><br>
        Please initiate renewal or extension process.
        """
    )
    create_system_notification(
        user=doc.owner,
        subject="Document Expiry Reminder",
        message=f"Document {doc.name} is expiring on {expiry_date}",
        reference_name=doc.name
    )

def send_expired_notification(doc, expiry_date):
    recipient = frappe.db.get_value("User", doc.owner, "email")
    if not recipient:
        return
    frappe.sendmail(
        recipients=[recipient],
        subject="Document Expired",
        message=f"""
        <b>Alert:</b><br><br>
        Document: {doc.name}<br>
        Applicant: {doc.applicant}<br>
        Expired On: {expiry_date}<br><br>
        Immediate action required.
        """
    )
    create_system_notification(
        user=doc.owner,
        subject="Document Expired",
        message=f"Document {doc.name} expired on {expiry_date}",
        reference_name=doc.name
    )

def create_system_notification(user, subject, message, reference_name):
    frappe.get_doc({
        "doctype": "Notification Log",
        "subject": subject,
        "email_content": message,
        "for_user": user,
        "type": "Alert",
        "document_type": "Document Application",
        "document_name": reference_name
    }).insert(ignore_permissions=True)
