import frappe
from frappe import _

def on_submit(self, method):
    # Only proceed if the stock entry purpose is Material Issue
    if self.purpose != "Material Issue":
        return

    for row in self.items:
        if row.custom_wbs:
            wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
            if not wbs_doc:
                frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
            
            # Check if enough on-hand quantity is available
            if row.qty > wbs_doc.custom_qty_in_hand:
                frappe.throw(
                    _("Insufficient on-hand quantity available for {0}. Requested: {1}, Available: {2}")
                    .format(row.custom_cost_code, row.qty, wbs_doc.custom_qty_in_hand)
                )
            
            # Adjust quantities: subtract from on-hand and add to consumed_quantity
            wbs_doc.custom_qty_in_hand -= row.qty
            wbs_doc.consumed_quantity = int (wbs_doc.consumed_quantity) + row.qty
            
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
    # Only proceed if the stock entry purpose is Material Issue
    if self.purpose != "Material Issue":
        return

    for row in self.items:
        if row.custom_wbs:
            try:
                wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
                if not wbs_doc:
                    frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
                
                # Reverse the changes: add back to on-hand and subtract from consumed_quantity
                wbs_doc.custom_qty_in_hand += row.qty
                wbs_doc.consumed_quantity -= row.qty
                
                wbs_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(
                    _("Failed to restore quantity for WBS Item {0}. Please try again.")
                    .format(row.custom_wbs)
                )
