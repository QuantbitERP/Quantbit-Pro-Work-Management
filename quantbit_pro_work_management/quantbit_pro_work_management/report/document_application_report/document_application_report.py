# Copyright (c) 2026, Quantbit Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Application ID",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Document Application",
            "width": 180,
        },
        {
            "label": "Applicant Full Name",
            "fieldname": "applicant_full_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Document Category",
            "fieldname": "document_category",
            "fieldtype": "Link",
            "options": "Document Category",
            "width": 160,
        },
        {
            "label": "Document Type",
            "fieldname": "document_type",
            "fieldtype": "Link",
            "options": "Document Type",
            "width": 160,
        },
        {
            "label": "Transaction Type",
            "fieldname": "transaction_type",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Posting Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120,
        },
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("transaction_type"):
        conditions.append("transaction_type = %(transaction_type)s")
        values["transaction_type"] = filters["transaction_type"]

    if filters.get("applicant_full_name"):
        conditions.append("applicant_full_name LIKE %(applicant_full_name)s")
        values["applicant_full_name"] = f"%{filters['applicant_full_name']}%"

    if filters.get("status"):
        conditions.append("status = %(status)s")
        values["status"] = filters["status"]

    condition_query = ""
    if conditions:
        condition_query = "WHERE " + " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            name,
            applicant_full_name,
            document_category,
            document_type,
            transaction_type,
            posting_date,
            status
        FROM
            `tabDocument Application`
        {condition_query}
        ORDER BY posting_date DESC
        """,
        values,
        as_dict=True,
    )

