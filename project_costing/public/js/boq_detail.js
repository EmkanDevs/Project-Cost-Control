frappe.provide("frappe.treeview_settings");

frappe.treeview_settings["BOQ Details"] = {
    breadcrumb: "BOQ",
    title: __("BOQ Details"),
    root_label: "BOQ Details",
    get_tree_root: true, 
    get_tree_nodes: "project_costing.project_costing.doctype.boq_details.boq_details.get_children",

    get_label: function (node) {
        // Accessing boq_id:
        const boqId = node.data.boq_id; // This directly accesses it from the 'data' object
        return `${node.label} ([BOQ: ${boqId || "N/A"}]`;
    },

    // Fields used when adding a child node
    fields: [
        {
            fieldtype: "Data",
            fieldname: "name",
            label: __("BOQ Details"),
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
                const tree = frappe.views.trees["BOQ Details"];
                tree.new_node();
            }
        }
    ],

    extend_toolbar: true,

    onload: function (treeview) {
        frappe.treeview_settings["BOQ Details"].treeview = {};
        Object.assign(frappe.treeview_settings["BOQ Details"].treeview, treeview);
    }
};