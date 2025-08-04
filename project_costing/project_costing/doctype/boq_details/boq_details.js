// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("BOQ Details", {
	refresh(frm) {
        frm.add_custom_button(__('Project Cost Control'), function () {
            const boq = frm.doc.name || '';
            const project = frm.doc.project || "";
        
            // Add more filters if needed
            frappe.set_route(
                "project-cost-control",
                `boq_details=${encodeURIComponent(boq)}`,
                `project=${encodeURIComponent(project)}`,
            );
        }, __("Report"));
	},
});
