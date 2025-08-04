frappe.ui.form.on('BOQ', {
    
    uom_boq: function (frm) {
        (frm.doc.boq_details || []).forEach(row => {
            if (!row.uom && frm.doc.uom_boq) {
                row.uom = frm.doc.uom_boq;
            }
        });
        frm.refresh_field('boq_details');
    },
    item_group_boq: function (frm) {
        (frm.doc.boq_details || []).forEach(row => {
            if (!row.item_group && frm.doc.item_group_boq) {
                row.item_group = frm.doc.item_group_boq;
            }
        });
        frm.refresh_field('boq_details');
    },
    uom_wbs: function (frm) {
        (frm.doc.wbs_item || []).forEach(row => {
            if (!row.uom && frm.doc.uom_wbs) {
                row.uom = frm.doc.uom_wbs;
            }
        });
        frm.refresh_field('wbs_item');
    },
    item_group_wbs: function (frm) {
        (frm.doc.wbs_item || []).forEach(row => {
            if (!row.item_group && frm.doc.item_group_wbs) {
                row.item_group = frm.doc.item_group_wbs;
            }
        });
        frm.refresh_field('wbs_item');
    },
    refresh: function (frm) {
        frm.add_custom_button(__('Project Cost Control'), function () {
            const boq = frm.doc.name || '';
            const project = frm.doc.project || "";
        
            // Add more filters if needed
            frappe.set_route(
                "project-cost-control",
                `boq=${encodeURIComponent(boq)}`,
                `project=${encodeURIComponent(project)}`,
            );
        }, __("Report"));
        if (frm.doc.missing_item_created == 0 && frm.doc.details_fetched == 1){
        frm.add_custom_button('Create Missing Items', () => {
            frappe.call({
                method: 'project_costing.project_costing.doctype.boq.boq.create_items_for_boq',
                args: { boq: frm.doc.name },
                callback: function (r) {
                    if (r.message && r.message.created_items && r.message.created_items.length) {
                        frappe.msgprint(__('Total Created Items: ') + r.message.created_items.length);
                        // frm.set_value('missing_item_created', 1);
                        frm.reload_doc(); 
                    } else {
                        frappe.msgprint(__('No new items were created.'));
                    }
                }
            });
        })};
        if (frm.doc.details_fetched == 0 && frm.doc.boq_details_created == 1 && frm.doc.wbs_item_created == 1){
        frm.add_custom_button('Load BOQ Details & WBS Items', () => {
            frappe.call({
                method: 'project_costing.project_costing.doctype.boq.boq.get_child_data',
                args: {
                    boq: frm.doc.name
                },
                callback: function (r) {
                    if (r.message) {
                        const { boq_details, wbs_items } = r.message;

                        frm.clear_table('boq_details');
                        frm.clear_table('wbs_item');

                        boq_details.forEach(detail => {
                            const row = frm.add_child('boq_details');
                            Object.assign(row, detail);
                        });

                        wbs_items.forEach(item => {
                            const row = frm.add_child('wbs_item');
                            Object.assign(row, item);
                        });
                        frm.set_value('details_fetched', 1);
                        frm.refresh_field('boq_details');
                        frm.refresh_field('wbs_item');
                        frm.save()

                        frappe.msgprint('BOQ Details and WBS Items loaded.');
                    }
                }
            });
        });
        }
        if (frm.doc.boq_details_created === 0) {
            frm.add_custom_button(__('Import BOQ from Excel'), function () {
                const d = new frappe.ui.Dialog({
                    title: __('Import BOQ Items from Excel'),
                    fields: [
                        {
                            label: __('Excel File'),
                            fieldname: 'file',
                            fieldtype: 'Attach',
                            reqd: 1,
                            description: __('Upload an Excel file (.xlsx or .xls) with BOQ items data'),
                            onchange: function () {
                                let file = d.get_value('file');
                                if (file) {
                                    let ext = file.split('.').pop().toLowerCase();
                                    if (!['xlsx', 'xls'].includes(ext)) {
                                        frappe.msgprint({
                                            title: __('Invalid File Type'),
                                            indicator: 'red',
                                            message: __('Please upload an Excel file (.xlsx or .xls)')
                                        });
                                        d.set_value('file', ''); 
                                    }
                                }
                            }
                        }
                    ],
                    primary_action_label: __('Import'),
                    primary_action(values) {
                        if (!values.file) {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: __('Please select a file to import')
                            });
                            return;
                        }

                        frappe.call({
                            method: "project_costing.project_costing.doctype.boq.boq.import_boq_items_from_excel",
                            args: {
                                file_path: values.file,
                                boq_name: frm.doc.name,
                                project_name :frm.doc.project,
                                warehouse: frm.doc.warehouse
                            },
                            freeze: true,
                            freeze_message: __('Importing data...'),
                            callback(r) {
                                if (r.message && r.message.success > 0) {
                                    frm.set_value("boq_details_created", 1);
                                    frm.save(); 
                                    frappe.msgprint(__('BOQ items imported successfully!'));
                                    d.hide(); 
                                    frm.reload_doc(); 
                                } else if (r.message && r.message.failed && r.message.failed.length === r.message.total) {
                                    frappe.msgprint({
                                        title: __('Import Failed'),
                                        indicator: 'red',
                                        message: __('No BOQ items were imported. Please check the file format and data.')
                                    });
                                } else if (r.message && r.message.failed && r.message.failed.length > 0) {
                                    frappe.msgprint({
                                        title: __('Partial Import'),
                                        indicator: 'orange',
                                        message: __(`Successfully imported ${r.message.success} items. Failed to import ${r.message.failed.length} items.`)
                                    });
                                } else if (r.exc) {
                                    frappe.msgprint({
                                        title: __('Import Error'),
                                        indicator: 'red',
                                        message: __('An error occurred during BOQ import. Please check server logs.')
                                    });
                                    console.error(r.exc); 
                                }
                            },
                            error: function(err) {
                                frappe.msgprint({
                                    title: __('Server Error'),
                                    indicator: 'red',
                                    message: __(`An unexpected error occurred: ${err.message}`)
                                });
                            }
                        });
                    }
                });
                d.show(); 
            });
        }
        if (frm.doc.boq_details_created === 1 && frm.doc.wbs_item_created === 0) {
            frm.add_custom_button(__('Import WBS from Excel'), function () {
                const d = new frappe.ui.Dialog({
                    title: __('Import WBS Items from Excel'),
                    fields: [
                        {
                            label: __('Excel File'),
                            fieldname: 'file',
                            fieldtype: 'Attach',
                            reqd: 1,
                            description: __('Upload an Excel file (.xlsx or .xls) with WBS items data'),
                            onchange: function () {
                                let file = d.get_value('file');
                                if (file) {
                                    let ext = file.split('.').pop().toLowerCase();
                                    if (!['xlsx', 'xls'].includes(ext)) {
                                        frappe.msgprint({
                                            title: __('Invalid File Type'),
                                            indicator: 'red',
                                            message: __('Please upload an Excel file (.xlsx or .xls)')
                                        });
                                        d.set_value('file', ''); 
                                    }
                                }
                            }
                        }
                    ],
                    primary_action_label: __('Import'),
                    primary_action(values) {
                        if (!values.file) {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: __('Please select a file to import')
                            });
                            return;
                        }

                        frappe.call({
                            method: "project_costing.project_costing.doctype.wbs_item.wbs_item_import.import_wbs_from_file",
                            args: {
                                file_name: values.file,
                                boq_name: frm.doc.name,
                                project_name:frm.doc.project,
                                warehouse: frm.doc.warehouse
                            },
                            freeze: true,
                            freeze_message: __('Importing data...'),
                            callback(r) {
                                if (r.message && r.message.success > 0) {
                                    frappe.msgprint(__('WBS items imported successfully!'));
                                    frm.set_value("wbs_item_created", 1);
                                    frm.save(); 
                                    d.hide(); 
                                    frm.reload_doc(); 
                                } else if (r.message && r.message.failed && r.message.failed.length === r.message.total) {
                                    frappe.msgprint({
                                        title: __('Import Failed'),
                                        indicator: 'red',
                                        message: __('No WBS items were imported. Please check the file format and data.')
                                    });
                                } else if (r.message && r.message.failed && r.message.failed.length > 0) {
                                    frappe.msgprint({
                                        title: __('Partial Import'),
                                        indicator: 'orange',
                                        message: __(`Successfully imported ${r.message.success} items. Failed to import ${r.message.failed.length} items.`)
                                    });
                                }
                                else if (r.exc) {
                                    frappe.msgprint({
                                        title: __('Import Error'),
                                        indicator: 'red',
                                        message: __('An error occurred during WBS import. Please check server logs.')
                                    });
                                    console.error(r.exc);
                                }
                            },
                            error: function(err) {
                                frappe.msgprint({
                                    title: __('Server Error'),
                                    indicator: 'red',
                                    message: __(`An unexpected error occurred: ${err.message}`)
                                });
                            }
                        });
                    }
                });
                d.show(); 
            });
        }

        frm.add_custom_button(__('BOQ Details'), () => {
            frappe.new_doc('BOQ Details', { boq: frm.doc.name,"project":frm.doc.project });
        }, 'Create'); 

        frm.add_custom_button(__('WBS Item'), () => { 
            frappe.new_doc('WBS item', { boq: frm.doc.name, "project": frm.doc.project });
        }, 'Create'); 

        frm.add_custom_button(__('Sales Order'), () => {
            frappe.db.get_value("Project", frm.doc.project, "customer")
                .then(res => {
                    const customer = res.message.customer;
                    if (!customer) {
                        frappe.msgprint("Customer not found in the linked Project.");
                        return;
                    }

                    frappe.call({
                        method: 'project_costing.project_costing.doctype.boq.boq.create_sales_order_from_boq',
                        args: {
                            boq_name: frm.doc.name,
                            customer: customer
                        },
                        callback: function (r) {
                            if (r.message) {
                                frappe.model.sync(r.message);
                                frappe.set_route('Form', r.message.doctype, r.message.name);
                            }
                        }
                    });
                });
        }, 'Create');


        frm.add_custom_button(__('BOQ Sheet'), function () {
            const url = "/files/BOQ Details.xlsx".replace(/#/g, "%23");
            window.open(url);
        }, 'Download'); 

        frm.add_custom_button(__('WBS Sheet'), function () {
            const url = "/files/WBS Item.xlsx".replace(/#/g, "%23");
            window.open(url);
        }, 'Download'); 

        frm.trigger("render_unlinked_wbs_html");

        frm.add_custom_button(__('Delete BOQ Details'), function () {
            frappe.confirm(
                'Are you sure you want to delete all BOQ Details for this BOQ? This action cannot be undone.',
                () => {
                    frappe.call({
                        method: 'project_costing.project_costing.doctype.boq.boq_delete.delete_boq_details',
                        args: {
                            boq: frm.doc.name
                        },
                        callback: function (r) {
                            if (r.message === 'success') {
                                // frm.clear_table("boq_details");
                                // frm.refresh_field("boq_details");
                                frappe.msgprint('All BOQ Details have been deleted successfully.');
                                frm.reload_doc(); 
                            } else if (r.exc) {
                                frappe.msgprint({
                                    title: __('Deletion Error'),
                                    indicator: 'red',
                                    message: __(`An error occurred during BOQ Detail deletion: ${r.exc}`)
                                });
                            }
                        },
                        error: function(err) {
                            frappe.msgprint({
                                title: __('Server Error'),
                                indicator: 'red',
                                message: __(`An unexpected error occurred: ${err.message}`)
                            });
                        }
                    });
                }
            );
        }, __('Actions')); 

        frm.add_custom_button(__('Delete WBS Items'), function () { 
            frappe.confirm(
                'Are you sure you want to delete all WBS items for this BOQ? This action cannot be undone.',
                () => {
                    frappe.call({
                        method: 'project_costing.project_costing.doctype.boq.boq_delete.delete_wbs_item', 
                        args: {
                            boq: frm.doc.name
                        },
                        callback: function (r) {
                            if (r.message === 'success') {
                                frm.clear_table("wbs_item");
                                frm.refresh_field("wbs_item");
                                frappe.msgprint('All WBS items have been deleted successfully.');
                                frm.reload_doc(); 
                            } else if (r.exc) {
                                frappe.msgprint({
                                    title: __('Deletion Error'),
                                    indicator: 'red',
                                    message: __(`An error occurred during WBS Item deletion: ${r.exc}`)
                                });
                            }
                        },
                        error: function(err) {
                            frappe.msgprint({
                                title: __('Server Error'),
                                indicator: 'red',
                                message: __(`An unexpected error occurred: ${err.message}`)
                            });
                        }
                    });
                }
            );
        }, __('Actions')); 

    
    },
    
    render_unlinked_wbs_html: function (frm) {
        const encodedFilter = encodeURIComponent(`["is", "not set"]`);
        const route = `/app/WBS Item?boq_details=${encodedFilter}`;
        const item_route = `/app/WBS Item?item=${encodedFilter}`;

        const html = `
            <div style="margin-top: 10px; padding: 10px 0;">
                <a href="${route}" class="btn btn-outline-primary" target="_blank" style="display: inline-block; margin-right: 10px;">
                    <b>View WBS Items Without BOQ Details</b>
                </a>
                <a href="${item_route}" class="btn btn-outline-primary" target="_blank" style="display: inline-block;">
                    <b>View WBS Items Without Item Connection</b>
                </a>
            </div>
        `;


        if (frm.fields_dict.custom_html) {
            frm.fields_dict.custom_html.$wrapper.html(html);
        }
    },

});