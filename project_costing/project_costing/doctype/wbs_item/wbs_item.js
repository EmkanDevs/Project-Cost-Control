frappe.ui.form.on('WBS item', {
    refresh: function(frm) {
        // Apply WBS visibility rules first
        apply_wbs_visibility_rules(frm);
        
        // Add custom button if level is less than 4
        if (frm.doc.level < 5) {
            frm.add_custom_button(__('Add Child WBS Item'), function() {
                frappe.new_doc('WBS item', {
                    parent_wbs_item: frm.doc.name,  
                    project: frm.doc.project,       
                    level: frm.doc.level + 1        
                });
            }, __('Actions'));
        }

        // Add Report buttons
        frm.add_custom_button(__('Project Cost Control'), function () {
            const boq = frm.doc.name || '';
            const project = frm.doc.project || "";
        
            // Add more filters if needed
            frappe.set_route(
                "project-cost-control",
                `boq_detail=${encodeURIComponent(boq)}`,
                `project=${encodeURIComponent(project)}`,
            );
        }, __("Report"));

        // Add WBS Report button
        frm.add_custom_button(__('WBS Report'), function () {
            const wbs_item = frm.doc.name || '';
            const project = frm.doc.project || "";
        
            // Open WBS Report with filters
            frappe.set_route(
                "query-report",
                "WBS Report",{project: frm.doc.project,wbs_item: frm.doc.name}
            );
        }, __("Report"));
        

        
        frm.set_query("cost_center", function() {
            return {
                filters: {
                    parent_cost_center: "Divisions - CPC"
                }
            };
        });
        frm.set_query("boq_details", function() {
            return {
                filters: {
                    project: frm.doc.project
                }
            };
        });

        if (!frm.is_new() && frm.doc.level == 5) {

            // Button to create Material Request
            frm.add_custom_button(__('Create Material Request'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Enter Material Request Details'),
                    fields: [
                        {
                            label: __('Quantity'),
                            fieldname: 'qty',
                            fieldtype: 'Float',
                            reqd: 1
                        },
                        {
                            label: __('Warehouse'),
                            fieldname: 'warehouse',
                            fieldtype: 'Link',
                            options: 'Warehouse',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Create'),
                    primary_action(values) {
                        // Validate entered quantity against available_qty
                        if (values.qty > frm.doc.available_qty) {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: __('Requested quantity cannot be greater than available quantity ({0})', [frm.doc.available_qty])
                            });
                            return;
                        }

                        // Create Material Request
                        frappe.call({
                            method: "frappe.client.insert",
                            args: {
                                doc: {
                                    doctype: "Material Request",
                                    material_request_type: "Purchase",
                                    project: frm.doc.project,
                                    items: [{
                                        item_code: frm.doc.item,
                                        qty: values.qty,
                                        schedule_date: frappe.datetime.now_date(),
                                        warehouse: values.warehouse,
                                        custom_wbs: frm.doc.name,
                                        custom_cost_code: frm.doc.cost_code,
                                        custom_combined_code: frm.doc.combined_code,
                                        rate: frm.doc.unit_rate
                                    }]
                                }
                            },
                            callback: function(response) {
                                if (response.message) {
                                    frappe.set_route("Form", "Material Request", response.message.name);
                                }
                            }
                        });

                        d.hide();
                    }
                });

                d.show();
            }, __("Actions"));

            // Button to create Stock Entry (Material Issue)
            frm.add_custom_button(__('Create Stock Entry (Material Issue)'), function() {
                let d2 = new frappe.ui.Dialog({
                    title: __('Enter Stock Entry Details'),
                    fields: [
                        {
                            label: __('Quantity'),
                            fieldname: 'qty',
                            fieldtype: 'Float',
                            reqd: 1
                        },
                        {
                            label: __('Source Warehouse'),
                            fieldname: 'source_warehouse',
                            fieldtype: 'Link',
                            options: 'Warehouse',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Create'),
                    primary_action(values) {
                        // First check if WBS item exists and get its available quantity
                        frappe.call({
                            method: "frappe.client.get",
                            args: {
                                doctype: "WBS item",
                                name: frm.doc.name
                            },
                            callback: function(response) {
                                if (!response.message) {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        indicator: 'red',
                                        message: __('WBS Item {0} not found', [frm.doc.name])
                                    });
                                    return;
                                }
                                
                                let wbs_doc = response.message;
                                let available_qty = wbs_doc.available_qty;
                                
                                // Validate entered quantity against available quantity in WBS item
                                if (values.qty > available_qty) {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        indicator: 'red',
                                        message: __('Insufficient quantity available for {0}. Requested: {1}, Available: {2}', 
                                            [frm.doc.name, values.qty, available_qty])
                                    });
                                    return;
                                }
                                
                                // Existing validation against on-hand quantity
                                if (values.qty > frm.doc.custom_qty_in_hand) {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        indicator: 'red',
                                        message: __('Entered quantity ({0}) cannot be greater than on-hand quantity ({1})', 
                                            [values.qty, frm.doc.custom_qty_in_hand])
                                    });
                                    return;
                                }
            
                                // Create Stock Entry for Material Issue
                                frappe.call({
                                    method: "frappe.client.insert",
                                    args: {
                                        doc: {
                                            doctype: "Stock Entry",
                                            stock_entry_type: "Material Issue",
                                            project: frm.doc.project,
                                            items: [{
                                                item_code: frm.doc.item,
                                                qty: values.qty,
                                                posting_date: frappe.datetime.now_date(),
                                                s_warehouse: values.source_warehouse,
                                                custom_wbs: frm.doc.name,
                                                custom_cost_code: frm.doc.cost_code,
                                                custom_combined_code: frm.doc.combined_code,
                                                rate: frm.doc.unit_rate
                                            }]
                                        }
                                    },
                                    callback: function(response) {
                                        if (response.message) {
                                            frappe.set_route("Form", "Stock Entry", response.message.name);
                                        }
                                    }
                                });
            
                                d2.hide();
                            }
                        });
                    }
                });
            
                d2.show();
            }, __("Actions"));
        }
    },

    parent_wbs_item: function(frm) {
        if (frm.doc.parent_wbs_item) {
            frappe.model.with_doc("WBS item", frm.doc.parent_wbs_item, function(parent_doc) {
                frm.set_value("level", parent_doc.level + 1);
                frm.set_value("project", parent_doc.project);
            });
        }
    }
});


// Function to apply visibility rules
function apply_wbs_visibility_rules(frm) {
    if (frm.doc.level > 1) {
        frm.set_df_property('project', 'read_only', 1);  // Project fetched automatically
    }

    if (frm.doc.level < 5) {
        frm.set_df_property('combined_code', 'hidden', 1); // Hide for Levels 1-3
    } else {
        frm.set_df_property('combined_code', 'hidden', 0); // Show for Level 4
    }
}
