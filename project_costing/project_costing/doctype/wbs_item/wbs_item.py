import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
import re  
from erpnext.stock.utils import get_stock_balance


class WBSitem(NestedSet):
    def autoname(self):
        # Generate name based on a sequence
        last_number = frappe.db.get_value("WBS item", {}, "name", order_by="creation desc")
        
        if last_number:
            # Extract and increment the last number
            parts = last_number.split('-')
            if len(parts) > 1 and parts[-1].isdigit():
                new_number = int(parts[-1]) + 1
            else:
                new_number = 1  # Reset to 1 if last number part isn't valid
        else:
            new_number = 1  # Start at 1 if no WBS item exists

        # Format the new name (e.g., WBS-0001)
        new_name = f"WBS-{new_number:04d}"
        self.name = new_name  # Set the name field for the new record
        
        # Set a unique serial number, avoid None or empty value
        if not self.serial_no:
            self.serial_no = new_name  # Optionally use the name as the serial number
            
    def validate(self):
        existing_item_name = frappe.db.get_value("Item",filters={"item_name": self.item_code,"disabled": 0},fieldname="name")

        if existing_item_name:
            self.db_set("item",existing_item_name)
            self.item = existing_item_name
            if self.item:
                self.db_set("item_group",frappe.db.get_value("Item",self.item,"item_group"))
                self.db_set("uom",frappe.db.get_value("Item",self.item,"stock_uom"))
                self.db_set("item_name",frappe.db.get_value("Item",self.item,"item_name"))
        else:
            self.item = None 
        self.calculation_of_wbs_item()
            
    def calculation_of_wbs_item(self):
        if self.resource_rate and self.custom_total_resource_qty:
            self.budget_rate = self.resource_rate * self.custom_total_resource_qty
            
        if self.waste and self.budget_qty and self.resource_qty:
            self.custom_total_resource_qty = self.budget_qty * self.waste * self.resource_qty

        if self.custom_total_resource_qty and self.pr__reserved_qty and self.risk__qty and self.petty_cash_qty:
            self.available_amount = self.custom_total_resource_qty - (self.pr__reserved_qty + self.risk__qty + self.petty_cash_qty)

        if self.available_amount and self.resource_rate:
            self.available_amount = self.available_amount * self.resource_rate
            
        available_qty = get_stock_balance(self.item, self.warehouse)
        if available_qty:
            self.available_qty = available_qty
            self.custom_qty_in_hand = available_qty

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
import re  
from erpnext.stock.utils import get_stock_balance


class WBSitem(NestedSet):
    def autoname(self):
        # Generate name based on a sequence
        last_number = frappe.db.get_value("WBS item", {}, "name", order_by="creation desc")
        
        if last_number:
            # Extract and increment the last number
            parts = last_number.split('-')
            if len(parts) > 1 and parts[-1].isdigit():
                new_number = int(parts[-1]) + 1
            else:
                new_number = 1  # Reset to 1 if last number part isn't valid
        else:
            new_number = 1  # Start at 1 if no WBS item exists

        # Format the new name (e.g., WBS-0001)
        new_name = f"WBS-{new_number:04d}"
        self.name = new_name  # Set the name field for the new record
        
        # Set a unique serial number, avoid None or empty value
        if not self.serial_no:
            self.serial_no = new_name  # Optionally use the name as the serial number
            
    def validate(self):
        existing_item_name = frappe.db.get_value("Item",filters={"item_name": self.item_code,"disabled": 0},fieldname="name")

        if existing_item_name:
            self.db_set("item",existing_item_name)
            self.item = existing_item_name
            if self.item:
                self.db_set("item_group",frappe.db.get_value("Item",self.item,"item_group"))
                self.db_set("uom",frappe.db.get_value("Item",self.item,"stock_uom"))
                self.db_set("item_name",frappe.db.get_value("Item",self.item,"item_name"))
        else:
            self.item = None 
        self.calculation_of_wbs_item()
            
    def calculation_of_wbs_item(self):
        if self.resource_rate and self.custom_total_resource_qty:
            self.budget_rate = self.resource_rate * self.custom_total_resource_qty
            
        if self.waste and self.budget_qty and self.resource_qty:
            self.custom_total_resource_qty = self.budget_qty * self.waste * self.resource_qty

        if self.custom_total_resource_qty and self.pr__reserved_qty and self.risk__qty and self.petty_cash_qty:
            self.available_amount = self.custom_total_resource_qty - (self.pr__reserved_qty + self.risk__qty + self.petty_cash_qty)

        if self.available_amount and self.resource_rate:
            self.available_amount = self.available_amount * self.resource_rate
            
        available_qty = get_stock_balance(self.item, self.warehouse)
        if available_qty:
            self.available_qty = available_qty
            self.custom_qty_in_hand = available_qty
        # self.consumed_quantity = get_material_issue_summary(self.item, self.warehouse)

            
@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False):
    filters = {"parent_wbs_item": parent or ""}

    items = frappe.get_all(
        doctype,
        filters=filters,
        fields=[
            "name as value",       # required for tree ID
            "name as label",       # shown in get_label
            "cost_code as cost_code",
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
            "cost_code": "",
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


@frappe.whitelist()
def get_material_issue_total_qty(item_code, warehouse, from_date=None, to_date=None):
    try:
        # Build filters for stock entry
        filters = {
            "docstatus": 1,  # Only submitted entries
            "purpose": "Material Issue",
            "stock_entry_type": ["in", frappe.get_all("Stock Entry Type", filters={"purpose": "Material Issue"}, pluck="name")]
        }
        
        # Get all material issue stock entries
        stock_entries = frappe.get_all(
            "Stock Entry",
            filters=filters,
            fields=["name", "posting_date", "posting_time", "project", "remarks"]
        )
        
        total_qty = 0
        matching_entries = []
        
        for se in stock_entries:
            # Get items from each stock entry
            se_items = frappe.get_all(
                "Stock Entry Detail",
                filters={
                    "parent": se.name,
                    "item_code": item_code,
                    "s_warehouse": warehouse
                },
                fields=["qty", "transfer_qty", "basic_rate", "serial_no", "batch_no"]
            )
            
            for item in se_items:
                if item.qty > 0:
                    total_qty += item.qty
                    matching_entries.append({
                        "stock_entry": se.name,
                        "posting_date": se.posting_date,
                        "posting_time": se.posting_time,
                        "project": se.project,
                        "remarks": se.remarks,
                        "qty": item.qty,
                        "transfer_qty": item.transfer_qty,
                        "basic_rate": item.basic_rate,
                        "serial_no": item.serial_no,
                        "batch_no": item.batch_no
                    })
        
        # Apply date filters if provided
        if from_date or to_date:
            filtered_entries = []
            for entry in matching_entries:
                entry_date = entry["posting_date"]
                
                if from_date and entry_date < from_date:
                    continue
                if to_date and entry_date > to_date:
                    continue
                    
                filtered_entries.append(entry)
            
            # Recalculate total for filtered entries
            total_qty = sum(entry["qty"] for entry in filtered_entries)
            matching_entries = filtered_entries
        
        return {
            "total_qty": total_qty,
            "stock_entries": matching_entries,
            "count": len(matching_entries)
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_material_issue_total_qty: {str(e)}")
        return {
            "total_qty": 0,
            "stock_entries": [],
            "count": 0,
            "error": str(e)
        }


@frappe.whitelist()
def get_material_issue_summary(item_code, warehouse):
    try:
        # Get total quantity
        total_info = get_material_issue_total_qty(item_code, warehouse)
        
        if not total_info["stock_entries"]:
            return {
                "total_qty": 0,
                "latest_entry_date": None,
                "latest_entry": None,
                "entry_count": 0
            }
        
        # Get latest entry
        latest_entry = max(total_info["stock_entries"], key=lambda x: x["posting_date"])
        
        return {
            "total_qty": total_info["total_qty"],
            "latest_entry_date": latest_entry["posting_date"],
            "latest_entry": latest_entry["stock_entry"],
            "entry_count": total_info["count"]
        }
        
    except Exception as e:
        frappe.log_error(f"Error in get_material_issue_summary: {str(e)}")
        return {
            "total_qty": 0,
            "latest_entry_date": None,
            "latest_entry": None,
            "entry_count": 0,
            "error": str(e)
        }
            
@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False):
    filters = {"parent_wbs_item": parent or ""}

    items = frappe.get_all(
        doctype,
        filters=filters,
        fields=[
            "name as value",       # required for tree ID
            "name as label",       # shown in get_label
            "cost_code as cost_code",
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
            "cost_code": "",
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