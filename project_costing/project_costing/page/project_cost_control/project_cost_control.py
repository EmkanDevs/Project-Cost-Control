import frappe

DOCTYPE_CONFIG = {
    "Material Request": {
        "child_table": "Material Request Item",
        "parent_fields": ["name", "transaction_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs","custom_boq_details"],
        "date_field": "transaction_date"
    },
    "Purchase Order": {
        "child_table": "Purchase Order Item",
        "parent_fields": ["name", "transaction_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs","custom_boq_details"],
        "date_field": "transaction_date"
    },
    "Purchase Invoice": {
        "child_table": "Purchase Invoice Item",
        "parent_fields": ["name", "posting_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs","custom_boq_details"],
        "date_field": "posting_date"
    },
    "Expense Claim": {
        "child_table": "Expense Claim Detail",
        "parent_fields": ["name","posting_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs","custom_boq_details"],
        "date_field": "posting_date"
    },
    "Supplier Quotation": {
        "child_table": "Supplier Quotation Item",
        "parent_fields": ["name", "transaction_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs"],
        "date_field": "transaction_date"
    },
    "Request for Quotation": {
        "child_table": "Request for Quotation Item",
        "parent_fields": ["name", "transaction_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs","custom_boq_details"],
        "date_field": "transaction_date"
    },
    "Stock Entry": {
        "child_table": "Stock Entry Detail",
        "parent_fields": ["name", "posting_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs","custom_boq_details"],
        "date_field": "posting_date"
    },
    "Purchase Receipt": {
        "child_table": "Purchase Receipt Item",
        "parent_fields": ["name", "posting_date"],
        "child_fields": ["project", "custom_boq", "custom_wbs", "custom_boq_details"],
        "date_field": "posting_date"
    }
    # Add more doctypes as needed
}

@frappe.whitelist()
def get_purchasing_docs(start_date=None, end_date=None, project=None, boq=None, boq_detail=None, boq_details=None, doctype=None, dynamic_docname=None):
    results = []
    doctypes_to_process = [doctype] if doctype else DOCTYPE_CONFIG.keys()
    for doctype_name in doctypes_to_process:
        config = DOCTYPE_CONFIG.get(doctype_name)
        if not config:
            continue
        filters = []
        if start_date:
            filters.append([config["date_field"], '>=', start_date])
        if end_date:
            filters.append([config["date_field"], '<=', end_date])
        if dynamic_docname:
            filters.append(["name", "=", dynamic_docname])

        parent_meta = frappe.get_meta(doctype_name)
        available_parent_fields = [f.fieldname for f in parent_meta.fields]
        parent_fields = list(config["parent_fields"])
        if config["date_field"] not in parent_fields:
            parent_fields.append(config["date_field"])
        if doctype_name in ["Purchase Invoice", "Purchase Order", "Supplier Quotation"]:
            total_field = "grand_total"
            if total_field in available_parent_fields and total_field not in parent_fields:
                parent_fields.append(total_field)
            else:
                total_field = None
        else:
            total_field = None
            for candidate in ["grand_total", "total", "base_grand_total", "rounded_total", "net_total", "total_amount", "base_total"]:
                if candidate in available_parent_fields:
                    parent_fields.append(candidate)
                    total_field = candidate
                    break
        workflow_field = None
        for candidate in ["workflow_state", "status"]:
            if candidate in available_parent_fields:
                parent_fields.append(candidate)
                workflow_field = candidate
                break
        currency_field = None
        for candidate in ["currency", "base_currency"]:
            if candidate in available_parent_fields:
                parent_fields.append(candidate)
                currency_field = candidate
                break
        parent_docs = frappe.get_all(
            doctype_name,
            filters=filters,
            fields=parent_fields
        )
        child_meta = frappe.get_meta(config["child_table"])
        available_fields = [f.fieldname for f in child_meta.fields]
        # Ensure 'custom_wbs' is included in child_fields if available
        child_fields = [f for f in (config["child_fields"] + ["custom_wbs"]) if f in available_fields]
        for doc in parent_docs:
            child_filters = {"parent": doc.name}
            if project and "project" in available_fields:
                child_filters["project"] = project
            if boq and "custom_boq" in available_fields:
                child_filters["custom_boq"] = boq
            if boq_detail and "custom_wbs" in available_fields:
                child_filters["custom_wbs"] = boq_detail
            if boq_details and "custom_boq_details" in available_fields:
                child_filters["custom_boq_details"] = boq_details
            items = frappe.get_all(
                config["child_table"],
                filters=child_filters,
                fields=child_fields
            )
            for item in items:
                workflow_status = ""
                for candidate in ["workflow_state", "status"]:
                    if hasattr(doc, candidate):
                        workflow_status = getattr(doc, candidate)
                        break
                currency = None
                for candidate in ["currency", "base_currency"]:
                    if hasattr(doc, candidate):
                        currency = getattr(doc, candidate)
                        break
                if not currency:
                    currency = frappe.defaults.get_global_default('currency')
                results.append({
                    "doctype": doctype_name,
                    "name": doc.name,
                    "posting_date": getattr(doc, config["date_field"], None),
                    "total": getattr(doc, total_field, None) if total_field else None,
                    "currency": currency,
                    "workflow_status": workflow_status,
                    "project": getattr(item, "project", None),
                    "custom_boq": getattr(item, "custom_boq", None),
                    "custom_wbs": getattr(item, "custom_wbs", None),
                    "custom_boq_details": getattr(item, "custom_boq_details", None)
                })
    return results
