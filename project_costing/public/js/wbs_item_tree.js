frappe.provide("frappe.treeview_settings");

frappe.treeview_settings["WBS item"] = {
    breadcrumb: "WBS",
    title: __("WBS Item"),
    root_label: "WBS Items",
    get_tree_root: true, // You changed this from true to false, which means it will expect a root from get_tree_nodes if no parent is given. If you want a static "WBS Items" root, keep get_tree_root: true.
    get_tree_nodes: "project_costing.project_costing.doctype.wbs_item.wbs_item.get_children",


    get_label: function (node) {
        // Accessing cost_code:
        const costCode = node.data.cost_code; // This directly accesses it from the 'data' object

        // Accessing boq_id:
        const boqId = node.data.boq_id; // This directly accesses it from the 'data' object
        return `${node.label} (${costCode || "No Cost Code"}) [BOQ: ${boqId || "N/A"}]`;
    },

    // Fields used when adding a child node
    fields: [
        {
            fieldtype: "Data",
            fieldname: "name",
            label: __("WBS Name"),
            reqd: true
        },
        {
            fieldtype: "Data",
            fieldname: "cost_code",
            label: __("Cost Code"),
            reqd: true
        },
        {
            fieldtype: "Data",
            fieldname: "boq_id",
            label: __("BOQ ID"),
            reqd: true
        },
        {
            fieldtype: "Check",
            fieldname: "is_group",
            label: __("Is Group")
        }
    ],

    toolbar: [
        {
            label: __("Add Child"),
            condition: function (node) {
                return node.expandable;
            },
            click: function (node) {
                const tree = frappe.views.trees["WBS item"];
                tree.new_node();
            }
        }
    ],

    extend_toolbar: true,

    onload: function (treeview) {
        frappe.treeview_settings["WBS item"].treeview = {};
        Object.assign(frappe.treeview_settings["WBS item"].treeview, treeview);
    }
};