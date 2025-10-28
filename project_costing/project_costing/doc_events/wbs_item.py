import frappe

def get_purchase_order_items(doc_name, name):
    total = 0
    items = frappe.get_all(doc_name, filters = {"custom_boq": name.boq}, fields=["name", "qty", "custom_boq"])
    for item in items:
        if item.custom_boq == name.boq:
            total = total + item.qty
    name.po_reserved_qty = total
    frappe.db.set_value("WBS item", name.name, "po_reserved_qty", total, update_modified=False)
    frappe.db.commit()

def get_material_request_items(doc_name, name):
    total = 0
    docs = frappe.db.get_values(doc_name, {"material_request_type" : "Purchase"}, ["name"])
    for doc in docs:
        mr_doc = frappe.get_doc(doc_name, doc[0])
        for item in mr_doc.items:
            if item.custom_boq == name.boq:
                total = total + item.qty
    name.pr__reserved_qty = total
    frappe.db.set_value("WBS item", name.name, "pr__reserved_qty", total, update_modified=False)
    frappe.db.commit()

def update_petty_cash_data(self):
    total_petty_cash_qty = 0
    total_petty_cash_amount = 0
    purchase_receipts = frappe.get_all("Purchase Receipt", filters = {"is_petty_cash" : 1}, fields = ["name"])
    for pr in purchase_receipts:
        pr_doc = frappe.get_doc("Purchase Receipt", pr.name)
        for item in pr_doc.items:
            if item.custom_boq == self.boq:
                total_petty_cash_qty = total_petty_cash_qty + item.qty
                total_petty_cash_amount = total_petty_cash_amount + item.amount
    self.petty_cash_qty = total_petty_cash_qty
    self.petty_cash_amount = total_petty_cash_amount
    frappe.db.set_value("WBS item", self.name, "petty_cash_qty", total_petty_cash_qty, update_modified=False)
    frappe.db.set_value("WBS item", self.name, "petty_cash_amount", total_petty_cash_amount, update_modified=False)
    frappe.db.commit()
    
def update_wbs_items(self):
    get_material_request_items("Material Request", self)
    get_purchase_order_items("Purchase Order Item", self)
    update_petty_cash_data(self)

def validate(self, method):
    update_wbs_items(self)