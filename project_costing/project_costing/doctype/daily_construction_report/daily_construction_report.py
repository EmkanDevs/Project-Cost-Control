# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DailyConstructionReport(Document):
	def validate(self):
		if self.dcr_date:
			for row in self.daily_progress:
				if row.end_date:
					if self.dcr_date == row.end_date:
						row.db_set("activity_class","Actual")
					else:
						row.db_set("activity_class","Forecast")
