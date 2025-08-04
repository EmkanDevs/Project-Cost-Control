frappe.query_reports["WBS Tree"] = {
    filters: [
        {
            fieldname: "cost_code",
            label: __("Cost Code"),
            fieldtype: "Data",
        },
        {
            fieldname: "cost_center_code",
            label: __("Cost Center Code"),
            fieldtype: "Data",
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },
        {
            fieldname: "item",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item"
        }
    ],

    onload: function(report) {
        this._report = report;
        this._initializeReport();
    },

    _initializeReport: function() {
        this._addCustomStyles();
        this._setupEventHandlers();
    },

    _addCustomStyles: function() {
        const styles = document.createElement('style');
        styles.textContent = `
            .wbs-buttons {
                white-space: nowrap;
                display: inline-flex;
            }
            .wbs-buttons .btn {
                margin-right: 2px;
            }
            .wbs-buttons .btn-xs {
                padding: 1px 5px;
                font-size: 12px;
                line-height: 1.5;
                border-radius: 3px;
            }
        `;
        document.head.appendChild(styles);
    },

    _setupEventHandlers: function() {
        // Remove any existing event handlers
        $(document).off('click.wbsReport', '.add-wbs-btn, .goto-wbs-btn, .edit-ref-btn, .create-stock-entry-btn');
        
        // Go to WBS button handler
        $(document).on('click.wbsReport', '.goto-wbs-btn', (e) => {
            e.preventDefault();
            const $button = $(e.currentTarget);
            const wbsName = $button.attr('data-wbs-name');
            
            if (wbsName) {
                frappe.set_route('Form', 'WBS Item', wbsName);
            } else {
                frappe.msgprint(__('Unable to find WBS Item reference. Please refresh the report.'));
            }
        });

        // Add WBS button handler
        $(document).on('click.wbsReport', '.add-wbs-btn', (e) => {
            e.preventDefault();
            const $button = $(e.currentTarget);
            const wbsName = $button.attr('data-wbs-name');
            
            if (wbsName) {
                this._showAddWBSDialog({ name: wbsName });
            }
        });

        // Edit reference button handler
        $(document).on('click.wbsReport', '.edit-ref-btn', (e) => {
            e.preventDefault();
            const $button = $(e.currentTarget);
            const wbsName = $button.attr('data-wbs-name');
            
            if (wbsName) {
                this._showEditRefDialog({ name: wbsName });
            }
        });

        // Create Stock Entry button handler
        $(document).on('click.wbsReport', '.create-stock-entry-btn', (e) => {
            e.preventDefault();
            const $button = $(e.currentTarget);
            const wbsName = $button.attr('data-wbs-name');
            
            if (wbsName) {
                this._showCreateStockEntryDialog({ name: wbsName });
            }
        });
    },

    _showAddWBSDialog: function(wbsData) {
        const dialog = new frappe.ui.Dialog({
            title: __('Add WBS Item'),
            fields: [
                {
                    label: __('Parent WBS Item'),
                    fieldname: 'parent_wbs_item',
                    fieldtype: 'Data',
                    read_only: 1,
                    default: wbsData.name
                },
                {
                    label: __('Item'),
                    fieldname: 'item',
                    fieldtype: 'Link',
                    options: 'Item'
                },
                {
                    label: __('Item Group'),
                    fieldname: 'item_group',
                    fieldtype: 'Link',
                    options: 'Item Group'
                },
                {
                    label: __('BOQ Qty'),
                    fieldname: 'qty',
                    fieldtype: 'Float',
                    default: 0
                },
                {
                    label: __('Budget'),
                    fieldname: 'budget',
                    fieldtype: 'Currency',
                    default: 0
                },
                {
                    label: __('Budget Rate'),
                    fieldname: 'unit_rate',
                    fieldtype: 'Currency',
                    default: 0
                },
            ],
            primary_action_label: __('Create'),
            primary_action(values) {
                frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'WBS item',
                            parent_wbs_item: values.parent_wbs_item,
                            item: values.item,
                            item_group: values.item_group,
                            unit_rate: values.unit_rate,
                            qty: values.qty,
                            budget: values.budget,
                        }
                    },
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('WBS Item created successfully'),
                                indicator: 'green'
                            });
                            dialog.hide();
                            frappe.query_report.refresh();
                        }
                    }
                });
            }
        });
        dialog.show();
    },

    _showEditRefDialog: function(wbsData) {
        // First fetch the document data
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'WBS item',
                name: wbsData.name
            },
            callback: (response) => {
                if (response.message) {
                    const doc = response.message;
                    const dialog = new frappe.ui.Dialog({
                        title: __('Edit WBS Item'),
                        fields: [
                            {
                                label: __('Serial'),
                                fieldname: 'serial',
                                fieldtype: 'Data',
                                default: doc.serial
                            },
                            {
                                label: __('Serial No'),
                                fieldname: 'serial_no',
                                fieldtype: 'Data',
                                default: doc.serial_no
                            },
                            {
                                label: __('Short Description'),
                                fieldname: 'short_description',
                                fieldtype: 'Data',
                                default: doc.short_description
                            },
                            {
                                label: __('Item'),
                                fieldname: 'item',
                                fieldtype: 'Link',
                                options: 'Item',
                                default: doc.item
                            },
                            {
                                label: __('Item Group'),
                                fieldname: 'item_group',
                                fieldtype: 'Link',
                                options: 'Item Group',
                                default: doc.item_group
                            },
                            {
                                label: __('UOM'),
                                fieldname: 'uom',
                                fieldtype: 'Link',
                                options: 'UOM',
                                default: doc.uom
                            },
                            {
                                label: __('BOQ Qty'),
                                fieldname: 'qty',
                                fieldtype: 'Float',
                                default: doc.qty
                            },
                            {
                                label: __('Consumed Quantity'),
                                fieldname: 'consumed_quantity',
                                fieldtype: 'Float',
                                default: doc.consumed_quantity
                            },
                            {
                                label: __('Material Rate'),
                                fieldname: 'unit_cost',
                                fieldtype: 'Currency',
                                default: doc.unit_cost
                            },
                            {
                                label: __('Budget'),
                                fieldname: 'budget',
                                fieldtype: 'Currency',
                                default: doc.budget
                            },
                            {
                                label: __('PR Reserved Qty'),
                                fieldname: 'pr__reserved_qty',
                                fieldtype: 'Float',
                                default: doc.pr__reserved_qty
                            },
                            {
                                label: __('PO Reserved Qty'),
                                fieldname: 'po_reserved_qty',
                                fieldtype: 'Float',
                                default: doc.po_reserved_qty
                            },
                            {
                                label: __('Available Qty'),
                                fieldname: 'available_qty',
                                fieldtype: 'Float',
                                default: doc.available_qty
                            },
                            {
                                label: __('PO Reserved Amount'),
                                fieldname: 'total',
                                fieldtype: 'Currency',
                                default: doc.total
                            }
                        ],
                        primary_action_label: __('Update'),
                        primary_action(values) {
                            // Create an object with only the changed values
                            const updates = {};
                            for (const [key, value] of Object.entries(values)) {
                                if (value !== doc[key]) {
                                    updates[key] = value;
                                }
                            }

                            if (Object.keys(updates).length === 0) {
                                dialog.hide();
                                return;
                            }

                            frappe.call({
                                method: 'frappe.client.set_value',
                                args: {
                                    doctype: 'WBS item',
                                    name: wbsData.name,
                                    fieldname: updates
                                },
                                callback: function(r) {
                                    if (!r.exc) {
                                        frappe.show_alert({
                                            message: __('WBS Item updated successfully'),
                                            indicator: 'green'
                                        });
                                        dialog.hide();
                                        frappe.query_report.refresh();
                                    }
                                }
                            });
                        }
                    });
                    dialog.show();
                }
            }
        });
    },
    
    _showCreateStockEntryDialog: function(wbsData) {
        // First fetch the WBS item details
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'WBS item',
                name: wbsData.name
            },
            callback: (response) => {
                if (response.message) {
                    const wbsDoc = response.message;
                    
                    // Create the dialog for stock entry
                    const dialog = new frappe.ui.Dialog({
                        title: __('Create Purchase Request'),
                        fields: [
                            {
                                label: __('WBS Item'),
                                fieldname: 'wbs_item',
                                fieldtype: 'Link',
                                options: 'WBS Item',
                                default: wbsData.name,
                                read_only: 1
                            },
                            {
                                label: __('Item'),
                                fieldname: 'item',
                                fieldtype: 'Link',
                                options: 'Item',
                                default: wbsDoc.item,
                                read_only: 1
                            },
                            {
                                label: __('Available Quantity'),
                                fieldname: 'available_qty',
                                fieldtype: 'Float',
                                default: wbsDoc.available_qty,
                                read_only: 1
                            },
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
                            // Validate quantity
                            if (values.qty <= 0) {
                                frappe.msgprint({
                                    title: __('Error'),
                                    indicator: 'red',
                                    message: __('Quantity must be greater than zero')
                                });
                                return;
                            }
                            
                            // Validate against available quantity
                            if (values.qty > wbsDoc.available_qty) {
                                frappe.msgprint({
                                    title: __('Error'),
                                    indicator: 'red',
                                    message: __('Insufficient quantity available. Requested: {0}, Available: {1}', 
                                        [values.qty, wbsDoc.available_qty])
                                });
                                return;
                            }
                            
                            // Create Stock Entry
                            frappe.call({
                                method: "frappe.client.insert",
                                args: {
                                    doc: {
                                        doctype: "Material Request",
                                        material_request_type: "Purchase",
                                        project: wbsDoc.project,
                                        items: [{
                                            item_code: wbsDoc.item,
                                            qty: values.qty,
                                            schedule_date: frappe.datetime.now_date(),
                                            warehouse: values.source_warehouse,
                                            custom_wbs: wbsData.name,
                                            custom_cost_code: wbsDoc.cost_code,
                                            custom_combined_code: wbsDoc.combined_code,
                                            rate: wbsDoc.unit_rate
                                        }]
                                    }
                                },
                                callback: function(response) {
                                    if (response.message) {
                                        frappe.show_alert({
                                            message: __('Purchase Request created successfully'),
                                            indicator: 'green'
                                        });
                                        dialog.hide();
                                        frappe.set_route("Form", "Material Request", response.message.name);
                                    }
                                }
                            });
                        }
                    });
                    
                    dialog.show();
                } else {
                    frappe.msgprint(__('Unable to fetch WBS Item details. Please try again.'));
                }
            }
        });
    },

    _generateButtons: function(data) {
        // Safety check for data
        if (!data) {
            console.warn('No data provided to _generateButtons');
            return '';
        }
    
        // Get the WBS name from the appropriate field
        const wbsName = data.name || data.wbs_item || data.id;
        
        if (!wbsName) {
            console.warn('No WBS name found in data:', data);
            return '';
        }
    
        // "Add" button should always appear
        let buttons = `
            <div class="wbs-buttons">
                <button type="button" class="btn btn-xs btn-info goto-wbs-btn" 
                    data-wbs-name="${frappe.utils.escape_html(wbsName)}"
                    title="Go to WBS Item">
                    <i class="fa fa-external-link"></i>
                </button>`;

        if (data.level < 5){
            buttons += `<button type="button" class="btn btn-xs btn-success add-wbs-btn" 
                    data-wbs-name="${frappe.utils.escape_html(wbsName)}"
                    title="Add WBS Item">
                    <i class="fa fa-plus"></i>
                </button>`
        }
        if (data.level == 5){
            buttons += `
                <button type="button" class="btn btn-xs btn-warning edit-ref-btn" 
                    data-wbs-name="${frappe.utils.escape_html(wbsName)}"
                    title="Edit Reference">
                    <i class="fa fa-pencil"></i>
                </button>
                <button type="button" class="btn btn-xs btn-dark create-stock-entry-btn" 
                    data-wbs-name="${frappe.utils.escape_html(wbsName)}"
                    title="Create Stock Entry">
                    Create Purchase Request
                </button>`
        }
    
        buttons += `</div>`;
        return buttons;
    },
    
    formatter: function(value, row, column, data, default_formatter) {
        if (column.fieldname === "actions" && data) {
            // If data is a string, try to parse it
            if (typeof data === 'string') {
                try {
                    data = JSON.parse(data);
                } catch (e) {
                    console.error('Error parsing data:', e);
                }
            }
            return this._generateButtons(data);
        }
        return default_formatter(value, row, column, data);
    }
};