import frappe
from frappe.model.document import Document
import pandas as pd
import math
from frappe import _
from frappe.model.naming import make_autoname
from frappe.model.mapper import get_mapped_doc
from frappe.desk.form.linked_with import get_linked_docs
from frappe.utils import now_datetime
import time

class BOQ(Document):
    pass

def safe_float(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def safe_string(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()
    
def safe_int(value):
    """Convert value to integer safely"""
    if value is None or pd.isna(value):
        return 1
    try:
        return int(value)
    except (ValueError, TypeError):
        return 1
    
@frappe.whitelist()
def import_boq_items_from_excel(file_path: str, boq_name: str, project_name, warehouse, use_boq_id_hierarchy=False):
    file_doc = frappe.get_doc('File', {'file_url': file_path})
    absolute_path = file_doc.get_full_path()
    df = pd.read_excel(absolute_path, header=0)
    df = df.where(pd.notnull(df), None)

    column_map = {
        'item_cost_code': 'Item Cost Code',
        'item': 'Item',
        'boq_qty': 'BOQ Qty',
        'takeoff': 'TakeOff',
        'selling_rate': 'Selling Rate',
        'original_contract_price': 'Original Contract Price',
        'div_name': 'DIV. Name',
        'lvl': 'LvL',
        'boq_id': 'BOQ ID',
        'uom': 'Unit',
    }

    total = len(df)
    created = 0

    if use_boq_id_hierarchy:
        # Use BOQ ID based hierarchy approach
        return create_boq_id_hierarchy(df, boq_name, project_name, warehouse, column_map)
    else:
        # Use Level-based hierarchy approach (original)
        return create_level_based_hierarchy(df, boq_name, project_name, warehouse, column_map)

def create_level_based_hierarchy(df, boq_name, project_name, warehouse, column_map):
    """Original level-based hierarchy approach"""
    created = 0
    total = len(df)
    
    # Store created documents for parent lookup
    doc_map = {}  # {item_cost_code: doc_name}
    level_map = {}  # {level: last_doc_name}
    
    # Sort by level to ensure parents are created before children
    df_sorted = df.sort_values(by=[column_map['lvl']]).reset_index(drop=True)
    
    for index, row in df_sorted.iterrows():
        boq_id = safe_string(row.get(column_map['boq_id']))
        item_cost_code = safe_string(row.get(column_map['item_cost_code']))
        level = safe_int(row.get(column_map['lvl']))
        
        if not item_cost_code:
            continue

        try:
            doc = frappe.new_doc('BOQ Details')
            doc.boq = boq_name
            doc.warehouse = warehouse
            doc.item_cost_code = item_cost_code
            doc.item = safe_string(row.get(column_map['item']))
            doc.boq_qty = safe_float(row.get(column_map['boq_qty']))
            doc.takeoff = safe_float(row.get(column_map['takeoff']))
            doc.selling_rate = safe_float(row.get(column_map['selling_rate']))
            doc.original_contract_price = safe_float(row.get(column_map['original_contract_price']))
            doc.div_name = safe_string(row.get(column_map['div_name']))
            doc.boq_id = boq_id
            doc.project = project_name
            doc.lvl = level
            doc.parent = boq_name
            doc.parenttype = 'BOQ'
            doc.parentfield = 'items'
            doc.uom = safe_string(row.get(column_map['uom']))

            # Find parent based on level hierarchy
            parent_name = None
            for parent_level in range(level-1, 0, -1):
                if parent_level in level_map:
                    parent_name = level_map[parent_level]
                    break
            
            if parent_name:
                doc.parent_boq_details = parent_name

            doc.insert(ignore_permissions=True)
            created += 1
            
            # Store for parent lookup
            doc_map[item_cost_code] = doc.name
            level_map[level] = doc.name
            
            # Clear deeper levels to maintain proper hierarchy
            levels_to_remove = [l for l in level_map.keys() if l >= level]
            for l in levels_to_remove:
                if l != level:
                    level_map.pop(l, None)

            # Send realtime progress
            frappe.publish_realtime(
                "boq_import_progress",
                {"progress": (created / total) * 100},
                user=frappe.session.user
            )

        except Exception as e:
            frappe.log_error(f"Error importing BOQ item {item_cost_code}: {str(e)}")
            continue

    frappe.db.commit()

    # Mark groups based on hierarchy
    mark_groups_as_is_group(boq_name)

    frappe.db.set_value("BOQ", boq_name, "boq_details_created", 1)
    frappe.db.commit()

    frappe.publish_realtime("boq_import_progress", {"progress": 100}, user=frappe.session.user)
    frappe.msgprint(f"Total BOQ Details created: {created}")

    return {"success": created}

def create_boq_id_hierarchy(df, boq_name, project_name, warehouse, column_map):
    """BOQ ID based hierarchy approach - creates missing intermediate levels"""
    created = 0
    total = len(df)
    
    # First, create all existing items
    existing_items = {}
    all_rows = []
    
    for index, row in df.iterrows():
        boq_id = safe_string(row.get(column_map['boq_id']))
        item_cost_code = safe_string(row.get(column_map['item_cost_code']))
        
        if not item_cost_code:
            continue
        
        # Store the row for processing
        all_rows.append(row)
        
        # Create the document
        parent_name = find_parent_for_boq_id(boq_id, existing_items)
        doc = create_boq_detail_doc(row, boq_name, project_name, warehouse, parent_name, column_map)
        
        if doc:
            created += 1
            existing_items[item_cost_code] = doc.name
            if boq_id:
                existing_items[boq_id] = doc.name
            
            # Send realtime progress
            frappe.publish_realtime(
                "boq_import_progress",
                {"progress": (created / len(all_rows)) * 100},
                user=frappe.session.user
            )
    
    # Then create missing intermediate BOQ ID levels
    for row in all_rows:
        boq_id = safe_string(row.get(column_map['boq_id']))
        if not boq_id or '.' not in boq_id:
            continue
            
        # Create all parent levels for this BOQ ID
        parts = boq_id.split('.')
        for i in range(1, len(parts)):
            parent_boq_id = '.'.join(parts[:i])
            
            # If this parent doesn't exist, create it
            if parent_boq_id not in existing_items:
                # Find the appropriate DIV name for this parent
                div_name = find_div_name_for_boq_id(parent_boq_id, df, column_map)
                
                parent_row = {
                    column_map['item_cost_code']: f"PARENT-{parent_boq_id}",
                    column_map['item']: f"Parent Group {parent_boq_id}",
                    column_map['boq_id']: parent_boq_id,
                    column_map['takeoff']: 0,
                    column_map['lvl']: i + 3,  # Adjust level based on your structure
                    column_map['uom']: '',
                    column_map['boq_qty']: 0,
                    column_map['selling_rate']: 0,
                    column_map['original_contract_price']: 0,
                    column_map['div_name']: div_name or row.get(column_map['div_name'])
                }
                
                # Find grandparent if exists
                grandparent_id = None
                if i > 1:
                    grandparent_boq_id = '.'.join(parts[:i-1])
                    grandparent_id = existing_items.get(grandparent_boq_id)
                
                doc = create_boq_detail_doc(parent_row, boq_name, project_name, warehouse, grandparent_id, column_map)
                if doc:
                    created += 1
                    existing_items[parent_boq_id] = doc.name
                    existing_items[f"PARENT-{parent_boq_id}"] = doc.name

    frappe.db.commit()

    # Mark groups based on hierarchy
    mark_groups_as_is_group(boq_name)

    frappe.db.set_value("BOQ", boq_name, "boq_details_created", 1)
    frappe.db.commit()

    frappe.publish_realtime("boq_import_progress", {"progress": 100}, user=frappe.session.user)
    frappe.msgprint(f"Total BOQ Details created: {created}")

    return {"success": created}

def find_parent_for_boq_id(boq_id, existing_items):
    """Find parent for a given BOQ ID"""
    if not boq_id or '.' not in boq_id:
        return None
        
    parts = boq_id.split('.')
    for i in range(len(parts)-1, 0, -1):
        parent_boq_id = '.'.join(parts[:i])
        if parent_boq_id in existing_items:
            return existing_items[parent_boq_id]
    
    return None

def find_div_name_for_boq_id(parent_boq_id, df, column_map):
    """Find appropriate DIV name for a parent BOQ ID by looking at children"""
    for index, row in df.iterrows():
        boq_id = safe_string(row.get(column_map['boq_id']))
        if boq_id and boq_id.startswith(parent_boq_id + '.'):
            return safe_string(row.get(column_map['div_name']))
    return None

def create_boq_detail_doc(row, boq_name, project_name, warehouse, parent_name, column_map):
    """Helper function to create BOQ Detail document"""
    try:
        doc = frappe.new_doc('BOQ Details')
        doc.boq = boq_name
        doc.warehouse = warehouse
        doc.item_cost_code = safe_string(row.get(column_map['item_cost_code']))
        doc.item = safe_string(row.get(column_map['item']))
        doc.boq_qty = safe_float(row.get(column_map['boq_qty']))
        doc.takeoff = safe_float(row.get(column_map['takeoff']))
        doc.selling_rate = safe_float(row.get(column_map['selling_rate']))
        doc.original_contract_price = safe_float(row.get(column_map['original_contract_price']))
        doc.div_name = safe_string(row.get(column_map['div_name']))
        doc.boq_id = safe_string(row.get(column_map['boq_id']))
        doc.project = project_name
        doc.lvl = safe_int(row.get(column_map['lvl']))
        doc.parent = boq_name
        doc.parenttype = 'BOQ'
        doc.parentfield = 'items'
        doc.uom = safe_string(row.get(column_map['uom']))
        
        if parent_name:
            doc.parent_boq_details = parent_name
        
        doc.insert(ignore_permissions=True)
        return doc
    except Exception as e:
        frappe.log_error(f"Error creating BOQ detail: {str(e)}")
        return None

def mark_groups_as_is_group(boq_name):
    """Mark items that have children as groups"""
    child_parents = frappe.get_all(
        'BOQ Details',
        filters={'boq': boq_name, 'parent_boq_details': ['!=', '']},
        fields=['parent_boq_details']
    )
    parent_names = set(c['parent_boq_details'] for c in child_parents)
    for parent_name in parent_names:
        frappe.db.set_value('BOQ Details', parent_name, 'is_group', 1)

@frappe.whitelist()
def get_child_data(boq):
    if not boq:
        frappe.throw(_("BOQ ID is required"))

    boq_details = frappe.get_all(
        "BOQ Details", 
        filters={"boq": boq},
        fields=["name as boq_detail","item","uom","item_group","selling_rate","boq_qty","takeoff"] 
    )

    wbs_items = frappe.get_all(
        "WBS item",  
        filters={"boq": boq},
        fields=["item_code as item", "name as wbs_item","uom","item_group",]  
    )

    return {
        "boq_details": boq_details,
        "wbs_items": wbs_items
    }


@frappe.whitelist()
def generate_next_item_code(item_group):
    """
    Generates the next sequential item code based on the Item Group's naming series.
    """
    if not item_group:
        frappe.throw("Item Group is required to generate an Item Code.")

    naming_series = frappe.db.get_value("Item Group", item_group, "custom_group_code")
    if not naming_series:
        prefix = "".join([word[0] for word in item_group.split() if word]) + "-"
        naming_series = prefix + ".#####"

    return make_autoname(naming_series, "Item")

@frappe.whitelist()
def create_items_for_boq(boq):
    if not boq:
        frappe.throw("BOQ is required.")

    boq_doc = frappe.get_doc("BOQ", boq)
    item_names = []

    for table_name in ["boq_details", "wbs_item"]:
        for row in boq_doc.get(table_name):
            item_name = (row.item).strip()

            if not item_name:
                frappe.throw("Please set Item name")
                

            if not frappe.db.exists("Item", {"item_name": item_name}):
                truncated_name = item_name[:140]
                item_group = row.item_group

                if not item_group:
                    continue  

                new_item_code = generate_next_item_code(item_group)

                item = frappe.get_doc({
                    "doctype": "Item",
                    "item_code": new_item_code,
                    "item_name": truncated_name,
                    "item_group": item_group,
                    "stock_uom": row.uom or "Nos",  
                    "is_stock_item": row.is_stock_item,
                    "description":row.item,
                    "disabled": 0
                })
                item.insert(ignore_permissions=True)

                if table_name == "boq_details":
                    row.db_set("created_item",new_item_code)
                    frappe.db.set_value("BOQ Details",row.boq_detail,"item_code",new_item_code)
                    frappe.db.set_value("BOQ Details",row.boq_detail,"item_group",item_group)
                    frappe.db.set_value("BOQ Details",row.boq_detail,"uom",row.uom)
                elif table_name == "wbs_item":
                    row.db_set("created_item",new_item_code)
                    frappe.db.set_value("WBS item",row.wbs_item,"item",new_item_code)
                    frappe.db.set_value("WBS item",row.wbs_item,"item_group",item_group)
                    frappe.db.set_value("WBS item",row.wbs_item,"uom",row.uom)

                item_names.append(new_item_code)
            elif frappe.db.exists("Item", {"item_name": item_name}):
                if table_name == "boq_details":
                    doc = frappe.get_doc("Item", {"item_name": item_name})
                    row.db_set("created_item",doc.name)
                elif table_name == "wbs_item":
                    doc = frappe.get_doc("Item", {"item_name": item_name})
                    row.db_set("created_item",doc.name)
    boq_doc.db_set("missing_item_created",1)
    boq_doc.save(ignore_permissions=True)
    return {"created_items": item_names}


@frappe.whitelist()
def create_sales_order_from_boq(boq_name, customer):
    def postprocess(source_doc, target_doc):
        target_doc.customer = customer
        target_doc.custom_boq = boq_name

    return get_mapped_doc(
        "BOQ", boq_name,
        {
            "BOQ": {
                "doctype": "Sales Order",
            },
            "BOQ Items": {
                "doctype": "Sales Order Item",
                "field_map": {
                    "created_item": "item_code",
                    "item": "item_name",
                    "uom": "uom",
                    "selling_rate":"rate",
                    "boq_qty":"qty"
                },
                "add_if_empty": True
            }
        },
        target_doc=None,
        postprocess=postprocess
    )

@frappe.whitelist()
def created_task(boq_name):
    created_tasks_list = []

    boq_details = frappe.get_all("BOQ Details", filters={"boq": boq_name}, fields=["name", "item_cost_code", "boq", "item","project"])
    parent_task_map = {}  

    for row in boq_details:
        boq_task = frappe.new_doc("Task")
        boq_task.subject = row.item_cost_code or f"Task for BoQ Details {row.name}"
        boq_task.custom_boq = row.boq
        boq_task.project = row.project
        boq_task.custom_boq_details = row.name
        boq_task.exp_start_date = now_datetime()
        boq_task.description = row.item
        boq_task.is_group = 1
        boq_task.insert()  
        created_tasks_list.append(boq_task.name)

        parent_task_map[row.name] = boq_task.name

    wbs_items = frappe.get_all("WBS item", filters={"boq": boq_name}, fields=["name","item_code","short_description", "cost_code", "project", "boq", "boq_details"])

    for row in wbs_items:
        wbs_task = frappe.new_doc("Task")
        wbs_task.subject = row.short_description or f"Task for WBS {row.name}"
        wbs_task.custom_boq = row.boq
        wbs_task.project = row.project
        wbs_task.custom_wbs_item = row.name
        wbs_task.description = row.item_code
        wbs_task.exp_start_date = now_datetime()

        if row.boq_details and row.boq_details in parent_task_map:
            wbs_task.parent_task = parent_task_map[row.boq_details]

        wbs_task.insert()
        created_tasks_list.append(wbs_task.name)
    return {"created_task": created_tasks_list}
