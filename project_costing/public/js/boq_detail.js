frappe.provide("frappe.treeview_settings");

frappe.treeview_settings["BOQ Details"] = {
    breadcrumb: "BOQ",
    title: __("BOQ Details"),
    root_label: "BOQ Details",
    get_tree_root: true, 
    get_tree_nodes: "project_costing.project_costing.doctype.boq_details.boq_details.get_children",
    
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
        const amount = node.data.original_contract_price;
    
        const left = `${node.label} [BOQ: ${boqId}]`;
    
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