frappe.ui.form.on('Purchase Invoice', {
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
    }
});
