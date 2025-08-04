import frappe
from frappe import _

def on_submit(self, method):
    for row in self.items:
        if row.custom_wbs:
            wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
            if not wbs_doc:
                frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
            
            if row.qty > wbs_doc.po_reserved_qty:
                frappe.throw(
                    _( "Insufficient PO reserved quantity for {0}. Requested: {1}, Available: {2}")
                    .format(row.custom_cost_code, row.qty, wbs_doc.po_reserved_qty)
                )
            
            # Update quantities
            wbs_doc.po_reserved_qty -= row.qty
            wbs_doc.custom_qty_in_hand += row.qty
            
            try:
                wbs_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(
                    _( "Failed to update quantity for WBS Item {0}. Please try again.")
                    .format(row.custom_wbs)
                )

def on_cancel(self, method):
    for row in self.items:
        if row.custom_wbs:
            try:
                wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
                if not wbs_doc:
                    frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
                
                # Restore the quantities
                wbs_doc.po_reserved_qty += row.qty
                wbs_doc.custom_qty_in_hand -= row.qty
                
                wbs_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(
                    _( "Failed to restore quantity for WBS Item {0}. Please try again.")
                    .format(row.custom_wbs)
                )
