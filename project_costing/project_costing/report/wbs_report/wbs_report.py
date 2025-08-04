import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 210},
        {"label": _("Draft No."), "fieldname": "draft_no", "fieldtype": "Int", "width": 180},
        {"label": _("Draft Qty"), "fieldname": "draft_qty", "fieldtype": "Float", "width": 180},
        {"label": _("Draft Amount"), "fieldname": "draft_amount", "fieldtype": "Currency", "width": 180},
        {"label": _("Approved No."), "fieldname": "approved_no", "fieldtype": "Int", "width": 180},
        {"label": _("Approved Qty"), "fieldname": "approved_qty", "fieldtype": "Float", "width": 180},
        {"label": _("Approved Amount"), "fieldname": "approved_amount", "fieldtype": "Currency", "width": 180},
        {"label": _("Cancelled No."), "fieldname": "cancelled_no", "fieldtype": "Int", "width": 180},
        {"label": _("Cancelled Qty"), "fieldname": "cancelled_qty", "fieldtype": "Float", "width": 180},
        {"label": _("Cancelled Amount"), "fieldname": "cancelled_amount", "fieldtype": "Currency", "width": 180},
    ]

    data = []
    summary = []

    if not filters or not filters.get("project") or not filters.get("wbs_item"):
        return columns, data, None, summary

    project = filters["project"]
    wbs_item = filters["wbs_item"]

    # Fetch BOQ/WBS details for Number Cards
    summary = get_summary_data(project, wbs_item)
    
    # Doctype mapping (excluding Stock Entry as it will be handled separately)
    doc_map = [
        {"doctype": "Material Request", "child": "Material Request Item", "project_field": "c.project"},
        {"doctype": "Request for Quotation", "child": "Request for Quotation Item", "project_field": "c.project_name"},
        {"doctype": "Supplier Quotation", "child": "Supplier Quotation Item", "project_field": "c.project"},
        {"doctype": "Purchase Order", "child": "Purchase Order Item", "project_field": "c.project"},
        {"doctype": "Purchase Receipt", "child": "Purchase Receipt Item", "project_field": "c.project"},
        {"doctype": "Purchase Invoice", "child": "Purchase Invoice Item", "project_field": "c.project"},
        {"doctype": "Expense Claim", "child": "Expense Claim Detail", "project_field": "p.project"},
    ]

    status_map = {doctype: {0: "Draft", 1: "Approved", 2: "Cancelled"} for doctype in [d["doctype"] for d in doc_map]}

    # Process regular doctypes
    for doc in doc_map:
        doctype = doc["doctype"]
        child = doc["child"]
        project_field = doc["project_field"]

        qty_expr = get_qty_expression(child)
        amount_expr = get_amount_expression(child)

        sql = f"""
            SELECT p.docstatus, COUNT(c.name) as no, {qty_expr} as qty, {amount_expr} as amount
            FROM `tab{doctype}` p
            JOIN `tab{child}` c ON c.parent = p.name
            WHERE c.custom_wbs = %s AND {project_field} = %s
            GROUP BY p.docstatus
        """

        rows = frappe.db.sql(sql, (wbs_item, project), as_dict=True)

        row = {"type": doctype}
        for status_code, status_label in status_map[doctype].items():
            found = next((r for r in rows if r.docstatus == status_code), None)
            row[f"{status_label.lower()}_no"] = found["no"] if found else 0
            row[f"{status_label.lower()}_qty"] = float(found["qty"]) if found and found["qty"] else 0
            row[f"{status_label.lower()}_amount"] = float(found["amount"]) if found and found["amount"] else 0
        data.append(row)

    # Handle Stock Entry separately by stock_entry_type
    data.extend(get_stock_entry_data(project, wbs_item))

    return columns, data, None, None, summary


def get_amount_expression(child_table):
    if frappe.db.has_column(child_table, "amount"):
        return "SUM(c.amount)"
    elif frappe.db.has_column(child_table, "price_list_rate"):
        return "SUM(c.price_list_rate * c.qty)"
    elif frappe.db.has_column(child_table, "rate"):
        return "SUM(c.rate * c.qty)"
    elif frappe.db.has_column(child_table, "valuation_rate"):
        return "SUM(c.valuation_rate * c.transfer_qty)"
    elif frappe.db.has_column(child_table, "claim_amount"):
        return "SUM(c.claim_amount)"
    else:
        return "0"


def get_qty_expression(child_table):
    if frappe.db.has_column(child_table, "qty"):
        return "SUM(c.qty)"
    elif frappe.db.has_column(child_table, "transfer_qty"):
        return "SUM(c.transfer_qty)"
    else:
        return "0"

def get_summary_data(project, wbs_item):
    # Fetch BOQ/WBS details for Summary Section
    boq_data = frappe.db.get_value(
        "WBS item",
        {"name": wbs_item},
        ["boq_id", "qty", "unit_cost", "total_price","short_description","boq_details"],
        as_dict=True
    )
    
    project_data = frappe.db.get_value(
        "Project",
        {"name": project},
        ["project_name"],
        as_dict=True
    )
    
    boq_details = frappe.db.get_value(
        "BOQ Details",
        {"name": boq_data.get("boq_details")},
        ["item"],
        as_dict=True
    )

    if not boq_data:
        return []

    return [
        {"label": "Project", "value": project, "indicator": "blue"},
        {"label": "Serial No", "value": wbs_item, "indicator": "green"},
        {"label": "BOQ ID", "value": boq_data.get("boq_id") or "N/A", "indicator": "red"},
        {"label": "BOQ Qty", "value": boq_data.get("qty") or 0, "datatype": "Float", "indicator": "gray"},
        {"label": "Material Rate", "value": boq_data.get("unit_cost") or 0, "datatype": "Currency", "indicator": "red"},
        {"label": "Project", "value": (project_data.get("project_name") if project_data else "N/A"), "indicator": "blue"},
        {"label": "WBS Short Description", "value": boq_data.get("short_description") or "N/A", "indicator": "blue"},
        {"label": "BOQ Details Description", "value": (boq_details.get("item") if boq_details else "N/A"), "indicator": "blue"},
        {"label": "Total Price", "value": boq_data.get("total_price") or 0, "datatype": "Currency", "indicator": "green"},
    ]


def get_stock_entry_data(project, wbs_item):
    """Get Stock Entry data split by stock_entry_type for Material Issue and Material Receipt"""
    stock_entry_types = ["Material Issue", "Material Receipt"]
    data = []
    
    qty_expr = get_qty_expression("Stock Entry Detail")
    amount_expr = get_amount_expression("Stock Entry Detail")
    
    for stock_entry_type in stock_entry_types:
        sql = f"""
            SELECT p.docstatus, COUNT(c.name) as no, {qty_expr} as qty, {amount_expr} as amount
            FROM `tabStock Entry` p
            JOIN `tabStock Entry Detail` c ON c.parent = p.name
            WHERE c.custom_wbs = %s AND c.project = %s AND p.stock_entry_type = %s
            GROUP BY p.docstatus
        """
        
        rows = frappe.db.sql(sql, (wbs_item, project, stock_entry_type), as_dict=True)
        
        row = {"type": f"Stock Entry - {stock_entry_type}"}
        status_map = {0: "Draft", 1: "Approved", 2: "Cancelled"}
        
        # Determine multiplier based on stock entry type
        multiplier = -1 if stock_entry_type == "Material Issue" else 1
        
        for status_code, status_label in status_map.items():
            found = next((r for r in rows if r.docstatus == status_code), None)
            row[f"{status_label.lower()}_no"] = found["no"] if found else 0
            row[f"{status_label.lower()}_qty"] = float(found["qty"]) * multiplier if found and found["qty"] else 0
            row[f"{status_label.lower()}_amount"] = float(found["amount"]) * multiplier if found and found["amount"] else 0
        
        data.append(row)
    
    return data
