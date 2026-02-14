# Copyright (c) 2026, Quantbit Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Applicant(Document):
    def validate(self):
        self.handle_applicant_type()

    def handle_applicant_type(self):
        if self.applicant_type == "Employee":
            if not self.employee:
                frappe.throw("Employee is required when Applicant Type is Employee.")
            employee = frappe.db.get_value(
                "Employee",
                self.employee,
                ["employee_name", "date_of_birth", "gender"],
                as_dict=True
            )
            if not employee:
                frappe.throw("Unable to fetch Employee details.")
            self.full_name = employee.employee_name
            self.date_of_birth = employee.date_of_birth
            self.gender = employee.gender
        elif self.applicant_type == "External":
            if not self.full_name:
                frappe.throw("Full Name is required for External Applicant.")
