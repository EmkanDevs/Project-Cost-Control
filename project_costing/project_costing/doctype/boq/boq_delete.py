import frappe
from frappe import _
from frappe.desk.form.linked_with import get

def clear_document_references(docname, doctype):
    """
    Remove references of a document from all linked doctypes,
    including inside child tables.
    """
    linked_data = get(docname, doctype)  # ✅ Correct usage

    if not linked_data:
        return

    for linked_doctype, records in linked_data.items():
        for record in records:
            try:
                linked_doc = frappe.get_doc(linked_doctype, record['name'])
                updated = False

                # ✅ 1. Clear direct link fields
                for df in linked_doc.meta.get_link_fields():
                    if df.options == docname and getattr(linked_doc, df.fieldname) == doctype:
                        linked_doc.set(df.fieldname, None)
                        updated = True

                # ✅ 2. Check child tables for references
                for table_df in linked_doc.meta.get_table_fields():
                    for row in linked_doc.get(table_df.fieldname):
                        for child_df in frappe.get_meta(table_df.options).get_link_fields():
                            
                            if child_df.options == docname and getattr(row, child_df.fieldname) == doctype:
                                print("hellllllooooo")
                                row.set(child_df.fieldname, None)
                                updated = True

                if updated:
                    linked_doc.save(ignore_permissions=True)

            except Exception as e:
                frappe.log_error(f"Error clearing reference in {linked_doctype} {record['name']}: {str(e)}")

    return "References cleared"



@frappe.whitelist()
def delete_boq_details(boq):
    """
    Enqueue deletion of BOQ Details and BOQ Items as background job.
    """
    if not boq:
        frappe.throw(_("BOQ is required."))

    if not frappe.db.exists("BOQ", boq):
        frappe.throw(_("BOQ {0} does not exist.").format(boq))

    # ✅ Enqueue background job
    frappe.enqueue(
        "project_costing.project_costing.doctype.boq.boq_delete.background_delete_boq_details",
        queue='long',
        timeout=900,  # 15 minutes for large data
        job_name=f"Delete BOQ Details for {boq}",
        boq=boq
    )

    return _("BOQ Details deletion process has been queued. Check Background Jobs for status.")


def background_delete_boq_details(boq):
    """
    Background job: Delete all BOQ Details & BOQ Items for given BOQ.
    Does NOT delete the BOQ itself.
    """
    if not boq:
        frappe.throw(_("BOQ is required."))

    if not frappe.db.exists("BOQ", boq):
        frappe.throw(_("BOQ {0} does not exist.").format(boq))

    try:
        # Get all BOQ Details and BOQ Items before deletion
        boq_details_list = frappe.get_all("BOQ Details", filters={"boq": boq}, pluck="name")
        boq_items_list = frappe.get_all("BOQ Items", filters={"parent": boq}, pluck="name")

        frappe.logger().info(f"Found {len(boq_details_list)} BOQ Details and {len(boq_items_list)} BOQ Items to delete")

        # Clear references for each BOQ Detail document
        for detail_name in boq_details_list:
            clear_document_references("BOQ Details",detail_name)


        # Delete BOQ Details and BOQ Items
        for detail_name in boq_details_list:
            frappe.delete_doc("BOQ Details", detail_name, ignore_permissions=True, force=True)


        # Update BOQ flag
        frappe.db.set_value("BOQ", boq, "boq_details_created", 0)

        frappe.db.commit()
        frappe.logger().info("BOQ Details deletion completed successfully")
        return "success"

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in delete_boq_details: {str(e)}", "BOQ Deletion Error")
        frappe.throw(_("Failed to delete BOQ Details: {0}").format(str(e)))



@frappe.whitelist()
def delete_wbs_items(boq):
    """
    Delete all WBS Items linked to a BOQ and remove all references.
    """
    if not boq:
        frappe.throw(_("BOQ is required."))

    if not frappe.db.exists("BOQ", boq):
        frappe.throw(_("BOQ {0} does not exist.").format(boq))

    try:
        # Get all WBS items for this BOQ
        wbs_items = frappe.get_all("WBS item", filters={"boq": boq}, pluck="name")
        
        # Clear references for each WBS item
        for wbs_item in wbs_items:
            clear_document_references("WBS item",wbs_item, )
        
        # Delete WBS items
        frappe.db.delete("WBS item", {"boq": boq})
        
        # Clear child table inside BOQ
        frappe.db.delete("BOQ WBS Item", {"parent": boq})
        
        # Update BOQ flag
        frappe.db.set_value("BOQ", boq, "wbs_item_created", 0)
        
        frappe.db.commit()
        return "success"

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in delete_wbs_items: {str(e)}", "WBS Deletion Error")
        frappe.throw(_("Failed to delete WBS Items: {0}").format(str(e)))


@frappe.whitelist()
def delete_wbs_item(boq):
    """
    Enqueue WBS deletion as background job.
    """
    if not boq:
        frappe.throw(_("BOQ is required."))

    if not frappe.db.exists("BOQ", boq):
        frappe.throw(_("BOQ {0} does not exist.").format(boq))

    frappe.enqueue(
        "project_costing.project_costing.doctype.boq.boq_delete.background_delete_wbs_item",
        queue='long',   # or 'default' if it's a small job
        timeout=600,    # 10 minutes
        job_name=f"Delete WBS Items for {boq}",
        boq=boq
    )

    return _("WBS deletion process has been queued. You will be notified when it's done.")


def background_delete_wbs_item(boq):
    """
    Actual deletion logic for WBS Items in background.
    """
    try:
        wbs_items = frappe.get_all("WBS item", filters={"boq": boq}, pluck="name")

        for wbs_item in wbs_items:
            clear_document_references(wbs_item, "WBS item")  # ✅ Correct order

        frappe.db.delete("WBS item", {"boq": boq})
        frappe.db.delete("BOQ WBS Item", {"parent": boq})

        frappe.db.set_value("BOQ", boq, "wbs_item_created", 0)

        frappe.db.commit()
        frappe.logger().info(f"WBS Items for BOQ {boq} deleted successfully")

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error in background_delete_wbs_item: {str(e)}", "WBS Deletion Error")
        frappe.throw(_("Failed to delete WBS Items: {0}").format(str(e)))
