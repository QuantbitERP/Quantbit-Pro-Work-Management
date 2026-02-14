// Copyright (c) 2026, Quantbit Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Document Application Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "transaction_type",
            label: __("Application Type"),
            fieldtype: "Select",
            options: "\nNew Application\nRenewal\nExtension\nReplacement\nCancellation"
        },
        {
            fieldname: "applicant_full_name",
            label: __("Applicant Full Name"),
            fieldtype: "Data"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nSubmitted\nUnder Review\nWaiting Docs\nApproved\nRejected\nIssued\nActive\nRenewed\nExtended\nExpired\nCancelled"
        }
    ]
};

