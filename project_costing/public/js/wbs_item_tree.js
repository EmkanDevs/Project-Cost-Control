frappe.provide("frappe.treeview_settings");

frappe.treeview_settings["WBS item"] = {
    breadcrumb: "WBS",
    title: __("WBS Item"),
    root_label: "WBS Items",
    get_tree_root: true, // You changed this from true to false, which means it will expect a root from get_tree_nodes if no parent is given. If you want a static "WBS Items" root, keep get_tree_root: true.
    get_tree_nodes: "project_costing.project_costing.doctype.wbs_item.wbs_item.get_children",


    get_label: function (node) {
        const is_root = node.is_root || node.data.is_root;
        if (is_root) {
            return `
                <div style="display:flex; width:100%;">
                    <div style="
                        flex:1;
                        text-align:left;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">
                        ${node.label}
                    </div>
                </div>
            `;
        }
        const boqId = node.data.boq_id || "N/A";
        const amount = node.data.qty;
    
        const left = `${node.label} [BOQ ID: ${boqId}]`;
    
        const right = (amount !== null && amount !== undefined)
            ? format_currency(amount)
            : "";
    
            return `
            <div style="
                display: flex;
                width: 100%;
            ">
                <!-- LEFT: sticks hard-left -->
                <div style="
                    flex: 1;
                    text-align: left;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                ">
                    ${left}
                </div>
    
                <!-- RIGHT: sticks hard-right -->
                <div style="
                    flex: 0 0 auto;
                    text-align: right;
                    margin-left: 16px;
                    white-space: nowrap;
                    color: var(--muted-text, #6c6f72);
                ">
                    ${right}
                </div>
            </div>
        `;
    },

    filters: [
        {
            fieldname: "boq",
            fieldtype: "Link",
            options: "BOQ",
            label: "BOQ"
        },
        {
            fieldname: "boq_id",
            fieldtype: "Data",
            label: "BOQ ID"
        }
    ],
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