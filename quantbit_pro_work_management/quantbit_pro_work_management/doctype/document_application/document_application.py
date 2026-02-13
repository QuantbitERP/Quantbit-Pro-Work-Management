# Copyright (c) 2026, Quantbit Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days

class DocumentApplication(Document):
    
    def before_save(self):
        self.calculate_expiry()
        self.calculate_supporting_doc_expiry()

    def on_submit(self):
        self.update_previous_document_on_renewal()
        self.update_previous_document_on_extension()

    def validate(self):
        self.auto_fetch_previous_document()
        if self.allow_expiry_override and not self.override_reason:
            frappe.throw("Override Reason is required when Expiry Override is enabled.")
        self.validate_master_data()
        self.validate_transaction_rules()
        self.prevent_duplicate_active()
        self.validate_expiry_dates()
        self.set_employee_name()
        self.set_document_category()

    def set_employee_name(self):
        if self.applicant_type == "Employee":
            if not self.employee:
                frappe.throw("Employee is required when Applicant Type is Employee.")
            employee_name = frappe.db.get_value(
                "Employee", self.employee, "employee_name"
            )
            if not employee_name:
                frappe.throw("Unable to fetch Employee Name.")
            self.applicant_full_name = employee_name

    def set_document_category(self):
        if not self.document_type:
            return
        category = frappe.db.get_value(
            "Document Type", self.document_type, "document_category"
        )
        if not category:
            frappe.throw(
                f"Document Category is not defined in Document Type {self.document_type}"
            )
        self.document_category = category

    def validate_master_data(self):
        if self.document_category:
            category = frappe.get_doc("Document Category", self.document_category)
            if not category.is_active:
                frappe.throw("Selected Document Category is inactive.")
        if self.document_type:
            doc_type = frappe.get_doc("Document Type", self.document_type)
            if not doc_type.is_active:
                frappe.throw("Selected Document Type is inactive.")
            if self.document_category and doc_type.document_category != self.document_category:
                frappe.throw("Document Type does not belong to selected Category.")
            if self.transaction_type == "Renewal" and not doc_type.renewal_allowed:
                frappe.throw("Renewal is not allowed for this Document Type.")

    def validate_transaction_rules(self):
        if self.transaction_type not in ["Renewal", "Extension"]:
            return
        if self.transaction_type == "Renewal":
            previous_docname = self.previous_document
            action = "renewed"
        else:
            previous_docname = self.previous_referred_document
            action = "extended"
        if not previous_docname:
            frappe.throw("Previous Document is required.")
        previous = frappe.get_doc("Document Application", previous_docname)
        if previous.docstatus != 1:
            frappe.throw(
                f"This application cannot be {action} because the previous document "
                f"{previous.name} is not submitted."
            )
        if previous.status not in ["Active", "Issued"]:
            frappe.throw(
                f"Only Active / Issued documents can be {action}."
            )
        if previous.document_type != self.document_type:
            frappe.throw("Transaction must be for the same Document Type.")

    def auto_fetch_previous_document(self):
        if self.transaction_type not in ["Renewal", "Extension"]:
            return
        if self.transaction_type == "Renewal":
            field_name = "previous_document"
            expiry_field = "previous_expiry_date"
        else:
            field_name = "previous_referred_document"
            expiry_field = "previous_referred_expiry_date"
        if self.get(field_name):
            return
        previous = frappe.get_all(
            "Document Application",
            filters={
                "applicant": self.applicant,
                "document_type": self.document_type,
                "docstatus": 1,
                "status": ["in", ["Active", "Issued"]],
            },
            fields=["name"],
            order_by="creation desc",
            limit=1,
        )
        if previous:
            self.set(field_name, previous[0].name)
            prev_doc = frappe.get_doc("Document Application", previous[0].name)
            self.set(expiry_field, prev_doc.expiry_date)

    def calculate_expiry(self):
        if self.allow_expiry_override:
            return
        if self.status != "Issued":
            return
        if not self.document_type:
            return
        doc_type = frappe.get_doc("Document Type", self.document_type)
        if not doc_type.has_expiry:
            self.expiry_date = None
            self.new_expiry_date = None
            return
        if not doc_type.validity_days:
            frappe.throw("Validity Days not defined in Document Type.")
        if self.transaction_type == "New Application":
            if not self.issue_date:
                frappe.throw("Issue Date is required before Issuing.")
            self.expiry_date = add_days(
                self.issue_date, doc_type.validity_days
            )
        else:
            previous_docname = (
                self.previous_document
                if self.transaction_type == "Renewal"
                else self.previous_referred_document
            )

            previous = frappe.get_doc("Document Application", previous_docname)

            self.expiry_date = previous.expiry_date
            self.new_expiry_date = add_days(
                previous.expiry_date, doc_type.validity_days
            )

    def calculate_supporting_doc_expiry(self):
        for row in self.supporting_document:
            if not row.document_type:
                continue
            doc_type = frappe.get_doc("Document Type", row.document_type)
            if not doc_type.has_expiry:
                row.expiry_date = None
                continue
            if not doc_type.validity_days:
                frappe.throw(
                    f"Validity Days not defined for {row.document_type}"
                )
            if row.issue_date:
                row.expiry_date = add_days(
                    row.issue_date, doc_type.validity_days
                )

    def prevent_duplicate_active(self):
        if self.status != "Active":
            return
        existing = frappe.get_all(
            "Document Application",
            filters={
                "applicant": self.applicant,
                "document_type": self.document_type,
                "status": "Active",
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                "Another Active document already exists for this applicant and document type."
            )
    def validate_expiry_dates(self):
        if self.issue_date and self.expiry_date:
            if self.expiry_date <= self.issue_date:
                frappe.throw("Expiry Date must be after Issue Date.")

    def update_previous_document_on_renewal(self):
        if self.transaction_type != "Renewal":
            return
        previous = frappe.get_doc(
            "Document Application", self.previous_document
        )
        if previous.status in ["Active", "Issued"]:
            previous.status = "Renewed"
            previous.save(ignore_permissions=True)

    def update_previous_document_on_extension(self):
        if self.transaction_type != "Extension":
            return
        if not self.extended_date:
            frappe.throw("Extended Date is required for Extension.")
        previous = frappe.get_doc(
            "Document Application", self.previous_referred_document
        )
        if previous.status in ["Active", "Issued"]:
            previous.status = "Extended"
            previous.save(ignore_permissions=True)

