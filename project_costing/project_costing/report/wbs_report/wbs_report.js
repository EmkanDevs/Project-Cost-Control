// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["WBS Report"] = {
	"filters": [
		{
			fieldname: "project",
			label: "Project",
			fieldtype: "Link",
			options: "Project",
			reqd: 1
		},
		{
			fieldname: "wbs_item",
			label: "WBS Item",
			fieldtype: "Link",
			options: "WBS item",
			get_query: function (doc) {
				let project = frappe.query_report.get_filter_value('project');
				if (!project) return {};
				return {
					filters: {
						project: project
					}
				};
			}
		}
	]
};
