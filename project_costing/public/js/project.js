frappe.ui.form.on('Project', {
    refresh: function (frm) {
        // Add direct button (not inside "Actions")
        frm.add_custom_button(__('Import WBS from Excel'), function () {
            const d = new frappe.ui.Dialog({
                title: __('Import WBS Items from Excel'),
                fields: [
                    {
                        label: __('Excel File'),
                        fieldname: 'file',
                        fieldtype: 'Attach',
                        options: 'File',
                        reqd: 1,
                        description: __('Upload an Excel file (.xlsx or .xls) with WBS items data'),
                        onchange: function () {
                            let file = d.get_value('file');
                            if (file) {
                                let file_ext = file.split('.').pop().toLowerCase();
                                if (!['xlsx', 'xls'].includes(file_ext)) {
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
                primary_action: function (values) {
                    if (!values.file) {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: __('Please select a file to import')
                        });
                        return;
                    }

                    // Show progress bar
                    frappe.show_progress('Importing WBS Items', 30, 100, 'Please wait...');

                    frappe.call({
                        method: 'project_costing.project_costing.doctype.wbs_item.wbs_item_import.import_wbs_from_file',
                        args: {
                            file_name: values.file,
                            project: frm.doc.name  // Pass project name if needed
                        },
                        callback: function (response) {
                            frappe.hide_progress();

                            if (response.exc) {
                                frappe.msgprint({
                                    title: __('Import Failed'),
                                    indicator: 'red',
                                    message: response.exc[1] || __('Error occurred during import')
                                });
                            } else if (response.message) {
                                frappe.show_alert({
                                    message: __('Import completed successfully'),
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        },
                        error: function () {
                            frappe.hide_progress();
                            frappe.msgprint({
                                title: __('Import Failed'),
                                indicator: 'red',
                                message: __('Error occurred during import. Please try again.')
                            });
                        }
                    });

                    d.hide();
                }
            });

            d.show();
        });
    }
});
