frappe.pages['project-cost-control'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Project Cost Control',
        single_column: true
    });

    $(frappe.render_template("project_cost_control", {})).appendTo(page.body);

    const $refreshBtn = $('<button class="btn btn-secondary ml-2">Refresh</button>');
    $(page.page_actions).append($refreshBtn);

    const filters = {};

    filters.start_date = frappe.ui.form.make_control({
        parent: $('#start_date_select'),
        df: {
            fieldtype: 'Date',
            label: 'Start Date',
            fieldname: 'start_date',
            reqd: 1
        },
        render_input: true
    });
    filters.start_date.set_value(frappe.datetime.add_days(frappe.datetime.now_date(), -7));

    filters.end_date = frappe.ui.form.make_control({
        parent: $('#end_date_select'),
        df: {
            fieldtype: 'Date',
            label: 'End Date',
            fieldname: 'end_date',
            reqd: 1
        },
        render_input: true
    });
    filters.end_date.set_value(frappe.datetime.now_date());

    filters.project = frappe.ui.form.make_control({
        parent: $('#project_select'),
        df: {
            fieldtype: 'Link',
            options: 'Project',
            label: 'Project',
            fieldname: 'project',
            reqd: 1
        },
        render_input: true
    });

    filters.boq = frappe.ui.form.make_control({
        parent: $('#boq_select'),
        df: {
            fieldtype: 'Link',
            options: 'BOQ',
            label: 'BOQ',
            fieldname: 'boq',
        },
        render_input: true
    });
    filters.boq.get_query = function() {
        return {
            filters: {
                project: filters.project.get_value()
            }
        };
    };

    filters.boq_detail = frappe.ui.form.make_control({
        parent: $('#boq_detail_select'),
        df: {
            fieldtype: 'Link',
            options: 'WBS item', 
            label: 'WBS Item',
            fieldname: 'boq_detail',
        },
        render_input: true
    });
    filters.boq_detail.get_query = function() {
        return {
            filters: {
                project: filters.project.get_value()
            }
        };
    };

    filters.boq_details = frappe.ui.form.make_control({
        parent: $('#boq_details_select'),
        df: {
            fieldtype: 'Link',
            options: 'BOQ Details',
            label: 'BOQ Details',
            fieldname: 'boq_details',
        },
        render_input: true
    });
    // Set filter by project for BOQ Details (if it's a Link field)
    if (filters.boq_details.df.fieldtype === 'Link') {
        filters.boq_details.get_query = function() {
            return {
                filters: {
                    project: filters.project.get_value()
                }
            };
        };
    }

    // Add Doctype filter (only allow specific doctypes)
    filters.doctype = frappe.ui.form.make_control({
        parent: $('#doctype_select'),
        df: {
            fieldtype: 'Link',
            label: 'Doctype',
            fieldname: 'doctype',
            options: 'DocType'
        },
        render_input: true
    });
    // Restrict to only allowed doctypes
    filters.doctype.get_query = function() {
        return {
            filters: [
                ['name', 'in', [
                    'Material Request',
                    'Request for Quotation',
                    'Supplier Quotation',
                    'Purchase Order',
                    'Purchase Receipt',
                    'Purchase Invoice',
                    'Stock Entry',
                    'Expense Claim'
                ]]
            ]
        };
    };

    filters.dynamic_docname = frappe.ui.form.make_control({
        parent: $('#dynamic_docname_select'),
        df: {
            fieldtype: 'Dynamic Link',
            label: 'Document',
            fieldname: 'dynamic_docname',
            options: 'doctype', // will be set dynamically
            reqd: 0
        },
        render_input: true
    });

    const urlParams = new URLSearchParams(window.location.search);
    Object.keys(filters).forEach(key => {
        const val = urlParams.get(key);
        if (val && filters[key].set_value) {
            filters[key].set_value(val);
        }
    });

    wrapper.filters = filters;

    function updateUrlFromFilters() {
        const params = new URLSearchParams(window.location.search);
        Object.keys(filters).forEach(k => {
            const v = filters[k].get_value();
            if (v) params.set(k, v);
            else params.delete(k);
        });
        window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
    }
    Object.keys(filters).forEach(key => {
        if (filters[key].on) {
            filters[key].on('change', function() {
                console.log('Filter changed:', key, filters[key].get_value());
                updateUrlFromFilters();
            });
        }
        if (filters[key].$input) {
            filters[key].$input.on('change', function() {
                updateUrlFromFilters();
            });
        }
    });

    window.get_project_cost_filters = function () {
        return {
            start_date: filters.start_date.get_value(),
            end_date: filters.end_date.get_value(),
            project: filters.project.get_value(),
            boq: filters.boq.get_value(),
            boq_detail: filters.boq_detail.get_value(),
            boq_details: filters.boq_details.get_value(),
            doctype: filters.doctype.get_value(), // add doctype filter
            dynamic_docname: filters.dynamic_docname.get_value() // add dynamic docname filter
        };
    };

    async function fetchAndRenderProjectCostData() {
        const filter_values = get_project_cost_filters();
        if (!filter_values.start_date || !filter_values.end_date || !filter_values.project) {
            frappe.msgprint(__("Please fill all mandatory fields."));
            return;
        }
        console.log("Selected Filters:", filter_values);

        frappe.call({
            method: "project_costing.project_costing.page.project_cost_control.project_cost_control.get_purchasing_docs",
            args: filter_values, // doctype is now included in filter_values
            callback: function (r) {
                if (r.message) {
                    const data = r.message;

                    if (!Array.isArray(data) || data.length === 0) {
                        $('#project_cost_results').html(`<div class="alert alert-warning">No records found.</div>`);
                        return;
                    }

                    // No need to filter by doctype here, backend will do it
                    let filteredData = data;
                    let tableHtml = `<div class="table-responsive"><table class="table table-bordered table-sm">
                        <thead>
                            <tr>
                                <th>Doctype</th>
                                <th>Name</th>
                                <th>Posting Date</th>
                                <th>Project</th>
                                <th>BOQ</th>
                                <th>WBS Item</th>
                                <th>BOQ Details</th>
                                <th>Total</th>
                                <th>Workflow Status</th>
                            </tr>
                        </thead>
                        <tbody>`;
                    filteredData.forEach(row => {
                        tableHtml += `<tr>
                            <td>${row.doctype}</td>
                            <td><a href="/app/${frappe.router.slug(row.doctype)}/${row.name}" target="_blank">${row.name}</a></td>
                            <td>${row.posting_date || ''}</td>
                            <td>${row.project || ''}</td>
                            <td>${row.custom_boq || ''}</td>
                            <td>${row.custom_wbs || ''}</td>
                            <td>${row.custom_boq_details || ''}</td>
                            <td>${row.total ? `${frappe.format(row.total, {fieldtype: 'Currency'})}` : ''}</td>
                            <td>${row.workflow_status || ''}</td>
                        </tr>`;
                    });
                    tableHtml += `</tbody></table></div>`;
                    $('#project_cost_results').html(tableHtml);

                    const doctypeCounts = {};
                    const doctypeAmounts = {};
                    const doctypes = [
                        "Material Request", "Request for Quotation", "Supplier Quotation",
                        "Purchase Order", "Purchase Receipt", "Purchase Invoice",
                        "Stock Entry", "Expense Claim"
                    ];

                    doctypes.forEach(doctype => {
                        doctypeCounts[doctype] = 0;
                        doctypeAmounts[doctype] = 0;
                    });

                    data.forEach(row => {
                        if (row.doctype) {
                            doctypeCounts[row.doctype] = (doctypeCounts[row.doctype] || 0) + 1;
                            doctypeAmounts[row.doctype] = (doctypeAmounts[row.doctype] || 0) + (row.total || 0);
                        }
                    });

                    const labels = Object.keys(doctypeCounts);
                    const counts = Object.values(doctypeCounts);
                    const amounts = Object.values(doctypeAmounts);

                    const chartBackgroundColors = [
                        'rgba(54, 162, 235, 0.5)',
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(255, 206, 86, 0.5)',
                        'rgba(75, 192, 192, 0.5)',
                        'rgba(153, 102, 255, 0.5)',
                        'rgba(255, 159, 64, 0.5)',
                        'rgba(255, 99, 71, 0.5)',
                        'rgba(60, 179, 113, 0.5)'
                    ];
                    const chartBorderColors = [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)',
                        'rgba(255, 99, 71, 1)',
                        'rgba(60, 179, 113, 1)'
                    ];

                    const ctxCount = document.getElementById('project_cost_chart_count').getContext('2d');
                    if (window.projectCostCountChart) {
                        window.projectCostCountChart.destroy();
                    }
                    window.projectCostCountChart = new Chart(ctxCount, {
                        type: 'pie',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Number of Documents',
                                data: counts,
                                backgroundColor: chartBackgroundColors,
                                borderColor: chartBorderColors,
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: false,
                            plugins: {
                                legend: { display: true },
                                title: { display: true, text: 'Number of Documents by Doctype' }
                            },
                            onClick: function(evt, elements) {
                                if (elements.length > 0) {
                                    const chart = elements[0];
                                    const clickedLabel = this.data.labels[chart.index];
                                    const filteredData = data.filter(row => row.doctype === clickedLabel);
                                    let tableHtml = `<div class="table-responsive"><table class="table table-bordered table-sm">
                                        <thead>
                                            <tr>
                                                <th>Doctype</th>
                                                <th>Name</th>
                                                <th>Posting Date</th>
                                                <th>Project</th>
                                                <th>BOQ</th>
                                                <th>WBS Item</th>
                                                <th>BOQ Details</th>
                                                <th>Total</th>
                                                <th>Workflow Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>`;
                                    filteredData.forEach(row => {
                                        tableHtml += `<tr>
                                            <td>${row.doctype}</td>
                                            <td><a href="/app/${frappe.router.slug(row.doctype)}/${row.name}" target="_blank">${row.name}</a></td>
                                            <td>${row.posting_date || ''}</td>
                                            <td>${row.project || ''}</td>
                                            <td>${row.custom_boq || ''}</td>
                                            <td>${row.custom_wbs || ''}</td>
                                            <td>${row.custom_boq_details || ''}</td>
                                            <td>${row.total ? `${frappe.format(row.total, {fieldtype: 'Currency'})}` : ''}</td>
                                            <td>${row.workflow_status || ''}</td>
                                        </tr>`;
                                    });
                                    tableHtml += `</tbody></table></div>`;
                                    tableHtml += `<button id="reset_table_filter" class="btn btn-secondary btn-sm mt-2">Show All</button>`;
                                    $('#project_cost_results').html(tableHtml);
                                    $('#reset_table_filter').on('click', function() {
                                        let fullTableHtml = `<div class="table-responsive"><table class="table table-bordered table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Doctype</th>
                                                    <th>Name</th>
                                                    <th>Posting Date</th>
                                                    <th>Project</th>
                                                    <th>BOQ</th>
                                                    <th>WBS Item</th>
                                                    <th>BOQ Details</th>
                                                    <th>Total</th>
                                                    <th>Workflow Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>`;
                                        data.forEach(row => {
                                            fullTableHtml += `<tr>
                                                <td>${row.doctype}</td>
                                                <td><a href="/app/${frappe.router.slug(row.doctype)}/${row.name}" target="_blank">${row.name}</a></td>
                                                <td>${row.posting_date || ''}</td>
                                                <td>${row.project || ''}</td>
                                                <td>${row.custom_boq || ''}</td>
                                                <td>${row.custom_wbs || ''}</td>
                                                <td>${row.custom_boq_details || ''}</td>
                                                <td>${row.total ? `${frappe.format(row.total, {fieldtype: 'Currency'})}` : ''}</td>
                                                <td>${row.workflow_status || ''}</td>
                                            </tr>`;
                                        });
                                        fullTableHtml += `</tbody></table></div>`;
                                        $('#project_cost_results').html(fullTableHtml);
                                    });
                                }
                            }
                        }
                    });

                    const ctxAmount = document.getElementById('project_cost_chart_amount').getContext('2d');
                    if (window.projectCostAmountChart) {
                        window.projectCostAmountChart.destroy();
                    }
                    window.projectCostAmountChart = new Chart(ctxAmount, {
                        type: 'pie',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Total Amount by Doctype',
                                data: amounts,
                                backgroundColor: chartBackgroundColors,
                                borderColor: chartBorderColors,
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: false,
                            plugins: {
                                legend: { display: true },
                                title: { display: true, text: 'Total Amount by Doctype' }
                            },
                            onClick: function(evt, elements) {
                                if (elements.length > 0) {
                                    const chart = elements[0];
                                    const clickedLabel = this.data.labels[chart.index];
                                    const filteredData = data.filter(row => row.doctype === clickedLabel);
                                    let tableHtml = `<div class="table-responsive"><table class="table table-bordered table-sm">
                                        <thead>
                                            <tr>
                                                <th>Doctype</th>
                                                <th>Name</th>
                                                <th>Posting Date</th>
                                                <th>Project</th>
                                                <th>BOQ</th>
                                                <th>WBS Item</th>
                                                <th>BOQ Details</th>
                                                <th>Total</th>
                                                <th>Workflow Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>`;
                                    filteredData.forEach(row => {
                                        tableHtml += `<tr>
                                            <td>${row.doctype}</td>
                                            <td><a href="/app/${frappe.router.slug(row.doctype)}/${row.name}" target="_blank">${row.name}</a></td>
                                            <td>${row.posting_date || ''}</td>
                                            <td>${row.project || ''}</td>
                                            <td>${row.custom_boq || ''}</td>
                                            <td>${row.custom_wbs || ''}</td>
                                            <td>${row.custom_boq_details || ''}</td>
                                            <td>${row.total ? `${frappe.format(row.total, {fieldtype: 'Currency'})}` : ''}</td>
                                            <td>${row.workflow_status || ''}</td>
                                        </tr>`;
                                    });
                                    tableHtml += `</tbody></table></div>`;
                                    tableHtml += `<button id="reset_table_filter" class="btn btn-secondary btn-sm mt-2">Show All</button>`;
                                    $('#project_cost_results').html(tableHtml);
                                    $('#reset_table_filter').on('click', function() {
                                        let fullTableHtml = `<div class="table-responsive"><table class="table table-bordered table-sm">
                                            <thead>
                                                <tr>
                                                    <th>Doctype</th>
                                                    <th>Name</th>
                                                    <th>Posting Date</th>
                                                    <th>Project</th>
                                                    <th>BOQ</th>
                                                    <th>WBS Item</th>
                                                    <th>BOQ Details</th>
                                                    <th>Total</th>
                                                    <th>Workflow Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>`;
                                        data.forEach(row => {
                                            fullTableHtml += `<tr>
                                                <td>${row.doctype}</td>
                                                <td><a href="/app/${frappe.router.slug(row.doctype)}/${row.name}" target="_blank">${row.name}</a></td>
                                                <td>${row.posting_date || ''}</td>
                                                <td>${row.project || ''}</td>
                                                <td>${row.custom_boq || ''}</td>
                                                <td>${row.custom_wbs || ''}</td>
                                                <td>${row.custom_boq_details || ''}</td>
                                                <td>${row.total ? `${frappe.format(row.total, {fieldtype: 'Currency'})}` : ''}</td>
                                                <td>${row.workflow_status || ''}</td>
                                            </tr>`;
                                        });
                                        fullTableHtml += `</tbody></table></div>`;
                                        $('#project_cost_results').html(fullTableHtml);
                                    });
                                }
                            }
                        }
                    });
                }
            }
        });
    }

    page.set_primary_action('Get Data', fetchAndRenderProjectCostData);
    $refreshBtn.on('click', fetchAndRenderProjectCostData);

    window.addEventListener('resize', function () {
        if (window.projectCostCountChart) {
            window.projectCostCountChart.resize();
        }
        if (window.projectCostAmountChart) {
            window.projectCostAmountChart.resize();
        }
    });
};

frappe.pages['project-cost-control'].on_page_show = function (wrapper) {
    const route = frappe.get_route(); 
    const route_params = {};

    route.slice(1).forEach(part => {
        part = decodeURIComponent(part); 
        if (part.includes('=')) {
            const [key, value] = part.split('=');
            route_params[key] = value;
        }
    });

    const filters = wrapper.filters;
    if (!filters) return;

    if (route_params.boq) {
        filters.boq.set_value(route_params.boq);
    }
    if (route_params.project) {
        filters.project.set_value(route_params.project);
    }
    if (route_params.boq_detail) {
        filters.boq_detail.set_value(route_params.boq_detail);
    }
    if (route_params.boq_details) {
        filters.boq_details.set_value(route_params.boq_details);
    }
    if (route_params.doctype) {
        filters.doctype.set_value(route_params.doctype);
    }
    if (route_params.dynamic_docname) {
        filters.dynamic_docname.set_value(route_params.dynamic_docname);
    }

    if (route_params.boq || route_params.project || route_params.boq_detail || route_params.doctype || route_params.dynamic_docname) {
        setTimeout(() => {
            document.querySelector('.primary-action')?.click();
        }, 500); 
    }
};
