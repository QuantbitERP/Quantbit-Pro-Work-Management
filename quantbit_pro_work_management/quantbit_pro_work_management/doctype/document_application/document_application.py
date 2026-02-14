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
        self.update_previous_document_status()

    def validate(self):
        self.auto_fetch_previous_document()
        if self.allow_expiry_override and not self.override_reason:
            frappe.throw("Override Reason is required when Expiry Override is enabled.")
        self.set_document_category()
        self.set_employee_name()
        self.set_employee_personal_details()
        self.validate_master_data()
        self.validate_transaction_rules()
        self.prevent_duplicate_active()
        self.validate_expiry_dates()

    def set_employee_personal_details(self):
        if self.applicant_type != "Employee" or not self.employee:
            return
        employee = frappe.db.get_value(
            "Employee",
            self.employee,
            ["date_of_birth", "gender"],
            as_dict=True
        )
        if not employee:
            frappe.throw("Unable to fetch Employee details.")
        self.date_of_birth = employee.date_of_birth
        self.gender = employee.gender

    def set_employee_name(self):
        if self.applicant_type != "Employee":
            return
        if not self.employee:
            frappe.throw("Employee is required when Applicant Type is Employee.")
        name = frappe.db.get_value("Employee", self.employee, "employee_name")
        if not name:
            frappe.throw("Unable to fetch Employee Name.")
        self.applicant_full_name = name

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
        if not self.document_type:
            return
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
        previous = self.get_previous_document()
        action = "renewed" if self.transaction_type == "Renewal" else "extended"
        if not previous:
            frappe.throw("Previous Document is required.")
        if previous.docstatus != 1:
            frappe.throw(
                f"This application cannot be {action} because the previous document "
                f"{previous.name} is not submitted."
            )
        if previous.status not in ["Active", "Issued"]:
            frappe.throw(f"Only Active / Issued documents can be {action}.")
        if previous.document_type != self.document_type:
            frappe.throw("Transaction must be for the same Document Type.")

    def get_previous_document(self):
        if self.transaction_type == "Renewal":
            return frappe.get_doc("Document Application", self.previous_document)
        if self.transaction_type == "Extension":
            return frappe.get_doc("Document Application", self.previous_referred_document)
        return None

    def auto_fetch_previous_document(self):
        if self.transaction_type not in ["Renewal", "Extension"]:
            return
        field_map = {
            "Renewal": ("previous_document", "previous_expiry_date"),
            "Extension": ("previous_referred_document", "previous_referred_expiry_date"),
        }
        link_field, expiry_field = field_map[self.transaction_type]
        if self.get(link_field):
            return
        previous = frappe.get_all(
            "Document Application",
            filters={
                "applicant": self.applicant,
                "document_type": self.document_type,
                "docstatus": 1,
                "status": ["in", ["Active", "Issued"]],
            },
            fields=["name", "expiry_date"],
            order_by="creation desc",
            limit=1,
        )
        if previous:
            self.set(link_field, previous[0].name)
            self.set(expiry_field, previous[0].expiry_date)

    def calculate_expiry(self):
        if self.allow_expiry_override or self.status != "Issued" or not self.document_type:
            return
        doc_type = frappe.get_doc("Document Type", self.document_type)
        if not doc_type.has_expiry:
            self.expiry_date = None
            self.new_expiry_date = None
            return
        if not doc_type.validity_days:
            frappe.throw("Validity Days not defined in Document Type.")
        validity = doc_type.validity_days - 1
        if self.transaction_type == "New Application":
            if not self.issue_date:
                frappe.throw("Issue Date is required before Issuing.")
            self.expiry_date = add_days(self.issue_date, validity)
            return
        previous = self.get_previous_document()
        self.expiry_date = previous.expiry_date
        self.new_expiry_date = add_days(previous.expiry_date, validity)

    def calculate_supporting_doc_expiry(self):
        for row in self.supporting_document:
            if not row.document_type or not row.issue_date:
                continue
            doc_type = frappe.get_doc("Document Type", row.document_type)
            if not doc_type.has_expiry:
                row.expiry_date = None
                continue
            if not doc_type.validity_days:
                frappe.throw(f"Validity Days not defined for {row.document_type}")
            row.expiry_date = add_days(row.issue_date, doc_type.validity_days - 1)

    def prevent_duplicate_active(self):
        if self.status != "Active":
            return
        exists = frappe.get_all(
            "Document Application",
            filters={
                "applicant": self.applicant,
                "document_type": self.document_type,
                "status": "Active",
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(
                "Another Active document already exists for this applicant and document type."
            )

    def validate_expiry_dates(self):
        if self.issue_date and self.expiry_date and self.expiry_date <= self.issue_date:
            frappe.throw("Expiry Date must be after Issue Date.")

    def update_previous_document_status(self):
        if self.transaction_type not in ["Renewal", "Extension"]:
            return
        previous = self.get_previous_document()
        if previous.status not in ["Active", "Issued"]:
            return
        previous.status = "Renewed" if self.transaction_type == "Renewal" else "Extended"
        previous.save(ignore_permissions=True)
