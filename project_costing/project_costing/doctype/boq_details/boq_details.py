# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BOQDetails(Document):
    def validate(self):
        existing_item_name = frappe.db.get_value("Item",filters={"item_name": self.item,"disabled": 0},fieldname="name")

        if existing_item_name:
            self.db_set("item_code",existing_item_name)
            if self.item:
                self.db_set("item_group",frappe.db.get_value("Item",self.item_code,"item_group"))
                self.db_set("uom",frappe.db.get_value("Item",self.item_code,"stock_uom"))
                self.db_set("item_name",frappe.db.get_value("Item",self.item_code,"item_name"))
            else:
                self.item_code = None

@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **kwargs):

    # Extract BOQ filter (TreeView passes it as kwargs)
    boq = kwargs.get("boq")
    boq_id = kwargs.get("boq_id")

    filters = {
        "parent_boq_details": parent or ""
    }

    # IF BOQ FILTER APPLIED → add it to DB filter
    if boq:
        filters["boq"] = boq
    if boq_id:
        filters["boq_id"] = boq_id

    items = frappe.get_all(
        doctype,
        filters=filters,
        fields=[
            "name as value",
            "name as label",
            "boq_id",
            "is_group",
            "original_contract_price"
        ],
        order_by="name"
    )

    # Root handling
    if not parent and not items:
        return [{
            "value": "Root",
            "label": "WBS Root",
            "boq_id": "",
            "is_group": 1,
            "expandable": True,
            "original_contract_price": 0
        }]

    # Set expandable + ensure numeric amount
    for item in items:
        item.expandable = 1 if item.is_group else 0
        item.original_contract_price = item.original_contract_price or 0

    return items
