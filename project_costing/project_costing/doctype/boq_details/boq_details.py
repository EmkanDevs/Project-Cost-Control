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
def get_children(doctype, parent=None, is_root=False):
    filters = {"parent_boq_details": parent or ""}

    items = frappe.get_all(
        doctype,
        filters=filters,
        fields=[
            "name as value",       # required for tree ID
            "name as label",       # shown in get_label
            "boq_id",
            "is_group"
        ],
        order_by="name"
    )

    # If it's the root call and no items exist, return a default root
    if not parent and not items:
        return [{
            "value": "Root",
            "label": "WBS Root",
            "boq_id": "",
            "is_group": 1,
            "expandable": True  # Mark root as expandable
        }]
    
    # Process items to add the 'expandable' property
    for item in items:
        if item.is_group:
            item.expandable = True
        else:
            item.expandable = False # Explicitly set to false for non-group items

    return items