import frappe
from frappe.model.document import Document
import pandas as pd
import math
from frappe import _
from frappe.model.naming import make_autoname
from frappe.model.mapper import get_mapped_doc
from frappe.desk.form.linked_with import get_linked_docs



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

@frappe.whitelist()
def import_boq_items_from_excel(file_path: str, boq_name: str,project_name, warehouse):
    file_doc = frappe.get_doc('File', {'file_url': file_path})
    absolute_path = file_doc.get_full_path()
    df = pd.read_excel(absolute_path, header=0)
    df = df.where(pd.notnull(df), None)

    column_map = {
        'item_cost_code': 'Item Cost Code',
        'item': 'Item',
        'boq_qty': 'BOQ Qty',
        'selling_rate': 'Selling Rate',
        'original_contract_price': 'Original Contract Price',
        'div_name': 'DIV. Name',
        'lvl': 'LvL',
        'boq_id': 'BOQ ID',
        'uom':'Unit',
    }

    created = 0
    last_node_by_level = {}

    for index, row in df.iterrows():
        boq_id = safe_string(row.get(column_map['boq_id']))
        item_cost_code = safe_string(row.get(column_map['item_cost_code']))
        if not boq_id or not item_cost_code:
            continue

        try:
            level = int(row.get(column_map['lvl']))
        except (ValueError, TypeError):
            level = 1

        parent_name = None
        for l in sorted(last_node_by_level.keys(), reverse=True):
            if l < level:
                parent_name = last_node_by_level[l]
                break

        doc = frappe.new_doc('BOQ Details')
        doc.boq = boq_name
        doc.warehouse = warehouse
        doc.item_cost_code = item_cost_code
        doc.item = safe_string(row.get(column_map['item']))
        doc.boq_qty = safe_float(row.get(column_map['boq_qty']))
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

        if parent_name:
            doc.parent_boq_details = parent_name

        doc.insert(ignore_permissions=True)
        created += 1

        last_node_by_level[level] = doc.name

        for l in list(last_node_by_level.keys()):
            if l > level:
                last_node_by_level.pop(l)

    frappe.db.commit()

    child_parents = frappe.get_all(
        'BOQ Details',
        filters={'boq': boq_name, 'parent_boq_details': ['!=', '']},
        fields=['parent_boq_details']
    )
    parent_names = set(c['parent_boq_details'] for c in child_parents)
    for parent_name in parent_names:
        frappe.db.set_value('BOQ Details', parent_name, 'is_group', 1)
    frappe.db.set_value("BOQ",boq_name,"boq_details_created",1)
    frappe.db.commit()
    frappe.msgprint(f"Total BOQ Details created: {created}")
    return True




@frappe.whitelist()
def get_child_data(boq):
    if not boq:
        frappe.throw(_("BOQ ID is required"))

    boq_details = frappe.get_all(
        "BOQ Details", 
        filters={"boq": boq},
        fields=["name as boq_detail","item","uom","item_group","selling_rate","boq_qty"] 
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
