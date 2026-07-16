from __future__ import annotations

import frappe

from ...services.print_format_service import DynamicPrintFormatService


class DynamicPrintFormat(frappe.model.document.Document):
	def validate(self):
		service = DynamicPrintFormatService()
		normalized = service.normalize_document(
			{
				"name": self.name,
				"format_name": self.format_name,
				"dynamic_form_template": self.dynamic_form_template,
				"is_default": self.is_default,
				"is_active": self.is_active,
				"page_width": self.page_width,
				"page_height": self.page_height,
				"margin_top": self.margin_top,
				"margin_right": self.margin_right,
				"margin_bottom": self.margin_bottom,
				"margin_left": self.margin_left,
				"layout_json": self.layout_json,
			}
		)
		self.format_name = normalized["format_name"]
		self.dynamic_form_template = normalized["dynamic_form_template"]
		self.is_default = normalized["is_default"]
		self.is_active = normalized["is_active"]
		self.page_width = normalized["page_width"]
		self.page_height = normalized["page_height"]
		self.margin_top = normalized["margin_top"]
		self.margin_right = normalized["margin_right"]
		self.margin_bottom = normalized["margin_bottom"]
		self.margin_left = normalized["margin_left"]
		self.layout_json = normalized["layout_json"]
		self.template_snapshot_json = normalized["template_snapshot_json"]
