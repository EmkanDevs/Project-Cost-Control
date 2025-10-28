import frappe
from frappe import _
import json
from project_costing.project_costing.doc_events.wbs_item import get_material_request_items
        
def on_update(self, method):
    for item in self.items:
        wbs = frappe.get_doc("WBS item", item.custom_wbs)
        get_material_request_items("Material Request", wbs)
    
def on_submit(self, method):
    for row in self.items:
        if row.custom_wbs:
            wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
            if not wbs_doc:
                frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
                
            available_qty = wbs_doc.available_qty
            
            if row.qty > available_qty:
                frappe.throw(
                    _("Insufficient quantity available for {0}. Requested: {1}, Available: {2}")
                    .format(row.custom_wbs, row.qty, available_qty)
                )
            
            # Update the available quantity
            wbs_doc.available_qty = available_qty - row.qty
            wbs_doc.pr__reserved_qty=wbs_doc.pr__reserved_qty + row.qty
            
            try:
                wbs_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(
                    _("Failed to update quantity for WBS Item {0}. Please try again.")
                    .format(row.custom_wbs)
                )

def on_cancel(self, method):
    for row in self.items:
        if row.custom_wbs:
            try:
                wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
                if not wbs_doc:
                    frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
                
                # Restore the available quantity
                wbs_doc.available_qty = wbs_doc.available_qty + row.qty
                wbs_doc.pr__reserved_qty=wbs_doc.pr__reserved_qty - row.qty
                wbs_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(
                    _("Failed to restore quantity for WBS Item {0}. Please try again.")
                    .format(row.custom_wbs)
                )
                
@frappe.whitelist()
def get_boq_wbs_items(boq_names):
    import json

    if isinstance(boq_names, str):
        boq_names = json.loads(boq_names)

    # Filter BOQs with base_budget = 0
    
    valid_boqs = frappe.get_all(
        "BOQ",
        filters={
            "name": ["in", boq_names],
            "version": "Zero Base Budget"
        },
        pluck="name",
        ignore_permissions=True
    )

    if not valid_boqs:
        frappe.throw("No BOQ with base budget Zero found.")

    # Now fetch WBS items only for valid BOQs
    items = frappe.get_all(
        "BOQ WBS Item",
        filters={"parent": ["in", valid_boqs]},
        fields=["name", "wbs_item", "item", "created_item", "item_group", "uom"],
        ignore_permissions=True
    )

    item_options = []

    for i in items:
        item_name = i.get("item") or ""
        item_code = i.get("created_item")

        if item_code:
            label = f'{item_name} ({item_code})'
            item_options.append({
                "label": label,
                "value": item_code,
                "item_name": item_name,
                "item_code": item_code,
                "item_group": i.get("item_group") or "",
                "uom": i.get("uom") or "",
                "wbs_name": i.get("wbs_item"),
                "boq_wbs_item_row": i.get("name")
            })

    return item_options



