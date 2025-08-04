from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    # Debug information
    if not data:
        frappe.msgprint("No data found after processing. Raw query returned data but post-processing resulted in empty dataset.")
    
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "cost_code",
            "label": _("Cost Code"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "cost_center_code",
            "label": _("Financial Code"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "item_group",
            "label": _("Item Group"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "combined_code",
            "label": _("Combined Code"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "short_description",
            "label": _("Short Description"),
            "fieldtype": "Data",
            "width": 250
        },
        {
            "fieldname": "item",
            "label": _("Item"),
            "fieldtype": "Data",
            "width": 100
        },
         {
            "fieldname": "uom",
            "label": _("UOM"),
            "fieldtype": "Data",
            "width": 100
        },
         {
            "fieldname": "qty",
            "label": _("BOQ Qty"),
            "fieldtype": "Float",
            "width": 100
        },
         {
            "fieldname": "available_qty",
            "label": _("Available Qty"),
            "fieldtype": "Float",
            "width": 100
        },
         {
            "fieldname": "resource_qty",
            "label": _("Resource Qty"),
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "waste",
            "label": _("Waste"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "unit_cost",
            "label": _("Material Rate"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "unit_rate",
            "label": _("Budget Rate"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "budget",
            "label": _("Budget"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "total",
            "label": _("PO Reserved Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "actions",
            "label": _(""),
            "fieldtype": "Data",
            "width": 250
        },
    ]

def get_wbs_items(filters):
    conditions = []
    
    if filters and filters.get('parent_wbs_item'):
        conditions.append(f"parent_wbs_item = '{filters.get('parent_wbs_item')}'")
    
    if filters and filters.get('cost_code'):
        conditions.append(f"cost_code LIKE '%{filters.get('cost_code')}%'")
    
    if filters and filters.get('cost_center_code'):
        conditions.append(f"cost_center_code LIKE '%{filters.get('cost_center_code')}%'")
    
    if filters and filters.get('project'):
        conditions.append(f"project = '{filters.get('project')}'")
    
    if filters and filters.get('item'):
        conditions.append(f"item = '{filters.get('item')}'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    return frappe.db.sql(f"""
        SELECT 
            name,
            cost_code,
            cost_center_code,
            unit_rate,
            resource_qty,
            combined_code,
            serial,
            serial_no,
            qty,
            short_description,
            item_group,
            consumed_quantity,
            po_reserved_qty,
            available_qty,
            waste,
            pr__reserved_qty,
            budget,
            total,
            item,
            unit_cost,
            uom,
            level,
            parent_wbs_item,
            is_group
        FROM
            `tabWBS item`
        WHERE 
            {where_clause}
        ORDER BY serial, name
    """, as_dict=True)

def get_data(filters):
    wbs_items = get_wbs_items(filters)
    
    if not wbs_items:
        frappe.msgprint("No items returned from database query")
        return []
    
    # When dealing with filters, we need a different approach to ensure proper tree view
    # We'll fetch all parents of filtered items to maintain the hierarchy
    
    # Collect all filtered items
    filtered_items = {item.name: item for item in wbs_items}
    
    # Add parent-child relationships for the filtered items
    parent_child_map = {}
    all_parents = set()
    
    for item in wbs_items:
        if item.parent_wbs_item:
            parent_child_map.setdefault(item.parent_wbs_item, []).append(item.name)
            all_parents.add(item.parent_wbs_item)
    
    # Find parent items that aren't in our filtered result but need to be included
    missing_parents = all_parents - set(filtered_items.keys())
    
    # If we have missing parents, fetch them from the database
    if missing_parents:
        parent_items = frappe.db.sql(f"""
            SELECT 
                name,
                cost_code,
                cost_center_code,
                unit_rate,
                resource_qty,
                combined_code,
                serial,
                serial_no,
                qty,
                short_description,
                item_group,
                consumed_quantity,
                po_reserved_qty,
                available_qty,
                waste,
                pr__reserved_qty,
                budget,
                total,
                item,
                unit_cost,
                uom,
                level,
                parent_wbs_item,
                is_group
            FROM
                `tabWBS item`
            WHERE 
                name IN ({', '.join(["'" + p + "'" for p in missing_parents])})
        """, as_dict=True)
        
        # Add these parents to our filtered items
        for item in parent_items:
            filtered_items[item.name] = item
            if item.parent_wbs_item:
                parent_child_map.setdefault(item.parent_wbs_item, []).append(item.name)
                all_parents.add(item.parent_wbs_item)
    
    # Reconstruct the tree from top to bottom
    # First find all root items (items with no parent or parent not in our dataset)
    root_items = [name for name, item in filtered_items.items() 
                if not item.parent_wbs_item or item.parent_wbs_item not in filtered_items]
    
    # Sort root items by serial
    root_items.sort(key=lambda x: (filtered_items[x].serial or "", x))
    
    # Process the tree
    data = []
    
    def process_tree(name, level=0):
        item = filtered_items[name]
        
        data.append({
            "name": item.name,
            "unit_rate": item.unit_rate,
            "cost_code": item.cost_code,
            "resource_qty": item.resource_qty,
            "waste": item.waste,
            "combined_code": item.combined_code,
            "cost_center_code": item.cost_center_code,
            "item": item.item,
            "level": item.level,
            "unit_cost": item.unit_cost,
            "serial_no": item.serial_no,
            "po_reserved_qty": item.po_reserved_qty,
            "available_qty": item.available_qty,
            "pr__reserved_qty": item.pr__reserved_qty,
            "short_description": item.short_description,
            "item_group": item.item_group,
            "consumed_quantity": item.consumed_quantity,
            "budget": item.budget,
            "total": item.total,
            "uom": item.uom,
            "parent_wbs_item": item.parent_wbs_item,
            "indent": level,
            "qty": item.qty,
            "is_group": item.is_group
        })
        
        # Process children if any
        children = parent_child_map.get(name, [])
        children.sort(key=lambda x: (filtered_items[x].serial or "", x))
        
        for child in children:
            process_tree(child, level + 1)
    
    # Process each root item
    for root in root_items:
        process_tree(root)
    
    # If no data generated through the tree, fall back to showing all filtered items
    if not data and filtered_items:
        for name, item in filtered_items.items():
            data.append({
                "name": item.name,
                "unit_rate": item.unit_rate,
                "cost_code": item.cost_code,
                "resource_qty": item.resource_qty,
                "waste": item.waste,
                "combined_code": item.combined_code,
                "cost_center_code": item.cost_center_code,
                "item": item.item,
                "unit_cost": item.unit_cost,
                "serial_no": item.serial_no,
                "po_reserved_qty": item.po_reserved_qty,
                "available_qty": item.available_qty,
                "pr__reserved_qty": item.pr__reserved_qty,
                "short_description": item.short_description,
                "item_group": item.item_group,
                "consumed_quantity": item.consumed_quantity,
                "budget": item.budget,
                "total": item.total,
                "uom": item.uom,
                "parent_wbs_item": item.parent_wbs_item,
                "indent": 0,
                "qty": item.qty,
                "is_group": item.is_group
            })
    
    return data