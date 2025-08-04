import frappe
from frappe import _

def on_submit(self, method):
    for row in self.items:
        if row.custom_wbs:
            wbs_doc = frappe.get_doc("WBS item", row.custom_wbs)
            if not wbs_doc:
                frappe.throw(_("WBS Item {0} not found").format(row.custom_wbs))
            pr__reserved_qty = wbs_doc.pr__reserved_qty
            
            if row.qty > pr__reserved_qty:
                frappe.throw(
                    _("Insufficient quantity available for {0}. Requested: {1}, Available: {2}")
                    .format(row.custom_cost_code, row.qty, pr__reserved_qty)
                )
            if row.amount>wbs_doc.available_amount:
                frappe.throw(
                    _("Insufficient balance available for {0}. Requested: {1}, Available: {2}")
                    .format(row.custom_cost_code, row.amount, wbs_doc.available_amount)
                )
            
            # Update the available quantity
            wbs_doc.pr__reserved_qty = pr__reserved_qty - row.qty
            wbs_doc.po_reserved_qty= wbs_doc.po_reserved_qty+row.qty
            wbs_doc.total=wbs_doc.total+row.amount
            wbs_doc.available_amount=wbs_doc.available_amount-row.amount
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
                wbs_doc.pr__reserved_qty = wbs_doc.pr__reserved_qty + row.qty
                wbs_doc.po_reserved_qty= wbs_doc.po_reserved_qty-row.qty
                wbs_doc.total=wbs_doc.total-row.amount
                wbs_doc.available_amount=wbs_doc.available_amount+row.amount
                
                wbs_doc.save(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(
                    _("Failed to restore quantity for WBS Item {0}. Please try again.")
                    .format(row.custom_wbs)
                )