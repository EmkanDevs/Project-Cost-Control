frappe.ui.form.on('Purchase Receipt', {
    refresh: function (frm) {
        frm.fields_dict['items'].grid.get_field('custom_boq').get_query = function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                filters: {
                    project: row.project
                }
            };
        };
        frm.fields_dict['items'].grid.get_field('custom_boq_details').get_query = function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                filters: {
                    project: row.project
                }
            };
        };
        frm.fields_dict['items'].grid.get_field('custom_wbs').get_query = function (doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            return {
                filters: {
                    project: row.project
                }
            };
        };
    },
    custom_wbs_item_list: function(frm) {
        frappe.prompt(
            {
                label: 'Project',
                fieldname: 'project',
                fieldtype: 'Link',
                options: 'Project',
                reqd: 1
            },
            function(values) {
                const selected_project = values.project;

                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype: "BOQ",
                        filters: { project: selected_project },
                        fields: ["name"]
                    },
                    callback: function(res) {
                        const boq_names = res.message.map(r => r.name);
                        if (boq_names.length === 0) {
                            frappe.msgprint("No BOQs found for the selected project.");
                            return;
                        }

                        frappe.call({
                            method: "project_costing.project_costing.doc_events.material_request.get_boq_wbs_items",
                            args: { boq_names },
                            callback: function(r) {
                                const options = r.message || [];

                                if (options.length === 0) {
                                    frappe.msgprint("No WBS Items with linked Items found.");
                                    return;
                                }

                                const item_map = {};
                                const valid_item_codes = [];

                                for (let opt of options) {
                                    item_map[opt.item_code] = opt;
                                    valid_item_codes.push(opt.item_code);
                                }

                                frappe.prompt(
                                    {
                                        label: 'Select WBS Item',
                                        fieldname: 'selected_item',
                                        fieldtype: 'Link',
                                        options: 'Item',
                                        get_query: () => ({
                                            filters: [["Item", "name", "in", valid_item_codes]]
                                        }),
                                        description: 'Choose item code linked to WBS',
                                        reqd: 1
                                    },
                                    function(item_values) {
                                        const selected = item_map[item_values.selected_item];

                                        if (!selected) {
                                            frappe.msgprint("Selected item not found in WBS list.");
                                            return;
                                        }

                                        const row = frm.add_child("items");
                                        row.item_code = selected.item_code;
                                        row.item_name = selected.item_name;
                                        row.item_group = selected.item_group;
                                        row.uom = selected.uom;
                                        row.qty = 1;
                                        row.project = selected_project;
                                        row.custom_wbs = selected.wbs_name;  // ← Set custom WBS field
                                        frm.refresh_field("items");

                                        frappe.msgprint(`Added: ${selected.label}`);
                                    },
                                    'Choose WBS Item',
                                    'Add Item'
                                );
                            }
                        });
                    }
                });
            },
            'Select Project',
            'Next'
        );
    }
});
