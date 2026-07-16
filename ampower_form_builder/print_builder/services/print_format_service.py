from __future__ import annotations

import json
from dataclasses import dataclass

import frappe
from frappe import _

TEMPLATE_DOCTYPE = "Dynamic Form Template"
SUBMISSION_DOCTYPE = "Dynamic Form Submission"
PRINT_FORMAT_DOCTYPE = "Dynamic Print Format"

A4_PAGE_WIDTH = "210mm"
A4_PAGE_HEIGHT = "297mm"

DEFAULT_PAGE = {
	"page_width": A4_PAGE_WIDTH,
	"page_height": A4_PAGE_HEIGHT,
	"margin_top": "10mm",
	"margin_right": "10mm",
	"margin_bottom": "10mm",
	"margin_left": "10mm",
}

MATRIX_DEFAULT_ROWS = 2
MATRIX_DEFAULT_COLS = 2
MATRIX_DEFAULT_ROW_HEIGHT = 34
MATRIX_DEFAULT_HEADING_HEIGHT = 28

def _parse_json(value, fallback=None):
	if fallback is None:
		fallback = {}
	if not value:
		return fallback
	if isinstance(value, (dict, list)):
		return value
	if isinstance(value, str):
		try:
			return json.loads(value)
		except Exception:
			return fallback
	return fallback


def _as_float(value, fallback=0.0):
	try:
		number = float(value)
	except Exception:
		return fallback
	return number if number >= 0 else fallback


def _as_bool(value, default=False):
	if value in (1, "1", True, "true", "True"):
		return True
	if value in (0, "0", False, "false", "False"):
		return False
	return default


def _normalize_text(value, fallback=""):
	text = (value or fallback or "").strip()
	return text


def _normalize_alignment(value):
	alignment = _normalize_text(value, "left") or "left"
	return alignment if alignment in {"left", "center", "right"} else "left"


def _normalize_field_item(item):
	print_columns = item.get("print_columns")
	if isinstance(print_columns, str):
		print_columns = _parse_json(print_columns, [])
	if not isinstance(print_columns, list):
		print_columns = []
	fieldname = _normalize_text(item.get("fieldname"))
	return {
		"id": _normalize_text(item.get("id")) or fieldname,
		"kind": "field",
		"fieldname": fieldname,
		"fieldtype": _normalize_text(item.get("fieldtype")),
		"label": _normalize_text(item.get("label")) or fieldname,
		"print_columns": [_normalize_text(column) for column in print_columns if _normalize_text(column)],
		"show_label": _as_bool(item.get("show_label"), True),
		"x": _as_float(item.get("x")),
		"y": _as_float(item.get("y")),
		"width": max(_as_float(item.get("width"), 120.0), 0.0),
		"height": max(_as_float(item.get("height"), 24.0), 0.0),
		"font_size": max(_as_float(item.get("font_size"), 11.0), 0.0),
		"align": _normalize_alignment(item.get("align")),
		"style": _parse_json(item.get("style"), {}) if isinstance(item.get("style"), (str, dict)) else {},
	}


def _normalize_matrix_cell(cell, row, col):
	return {
		"id": _normalize_text(cell.get("id")) or f"{row}:{col}",
		"key": _normalize_text(cell.get("key")) or f"{row}:{col}",
		"row": row,
		"col": col,
		"fieldname": _normalize_text(cell.get("fieldname")),
		"label": _normalize_text(cell.get("label")) or _normalize_text(cell.get("fieldname")),
		"static_text": _normalize_text(cell.get("static_text")),
		"show_label": _as_bool(cell.get("show_label"), True),
		"align": _normalize_alignment(cell.get("align")),
		"row_span": max(int(_as_float(cell.get("row_span"), 1)), 1),
		"col_span": max(int(_as_float(cell.get("col_span"), 1)), 1),
		"style": _parse_json(cell.get("style"), {}) if isinstance(cell.get("style"), (str, dict)) else {},
	}


def _build_matrix_cells(rows, cols, cells):
	index = {}
	for cell in cells or []:
		if not isinstance(cell, dict):
			continue
		row = max(0, min(int(_as_float(cell.get("row"), 0)), rows - 1))
		col = max(0, min(int(_as_float(cell.get("col"), 0)), cols - 1))
		index[f"{row}:{col}"] = _normalize_matrix_cell(cell, row, col)

	result = []
	occupied = {}
	for row in range(rows):
		for col in range(cols):
			key = f"{row}:{col}"
			covered_by = occupied.get(key)
			if covered_by:
				empty_cell = _normalize_matrix_cell({}, row, col)
				empty_cell["covered_by"] = covered_by
				result.append(empty_cell)
				continue

			cell = index.get(key) or _normalize_matrix_cell({}, row, col)
			cell = _normalize_matrix_cell(cell, row, col)
			cell_row_span = max(min(int(cell.get("row_span", 1)), rows - row), 1)
			cell_col_span = max(min(int(cell.get("col_span", 1)), cols - col), 1)
			cell["row_span"] = cell_row_span
			cell["col_span"] = cell_col_span
			result.append(cell)

			if not cell.get("fieldname") and cell_row_span == 1 and cell_col_span == 1:
				continue

			for row_offset in range(cell_row_span):
				for col_offset in range(cell_col_span):
					target_row = row + row_offset
					target_col = col + col_offset
					if target_row >= rows or target_col >= cols:
						continue
					if target_row == row and target_col == col:
						continue
					occupied[f"{target_row}:{target_col}"] = cell.get("key")
	return result


def _matrix_height(matrix):
	rows = max(int(_as_float(matrix.get("rows"), MATRIX_DEFAULT_ROWS)), 1)
	row_height = max(_as_float(matrix.get("row_height"), MATRIX_DEFAULT_ROW_HEIGHT), 20.0)
	heading_height = 0.0 if _as_bool(matrix.get("show_heading"), True) is False else max(_as_float(matrix.get("heading_height"), MATRIX_DEFAULT_HEADING_HEIGHT), 16.0)
	return 20.0 + heading_height + (rows * row_height)


def _normalize_matrix_item(item):
	rows = max(int(_as_float(item.get("rows"), MATRIX_DEFAULT_ROWS)), 1)
	cols = max(int(_as_float(item.get("cols"), MATRIX_DEFAULT_COLS)), 1)
	row_height = max(_as_float(item.get("row_height"), MATRIX_DEFAULT_ROW_HEIGHT), 20.0)
	heading_height = max(_as_float(item.get("heading_height"), MATRIX_DEFAULT_HEADING_HEIGHT), 16.0)
	matrix = {
		"id": _normalize_text(item.get("id")),
		"kind": "matrix",
		"region": _normalize_text(item.get("region"), "body") if _normalize_text(item.get("region"), "body") in {"body", "header", "footer"} else "body",
		"heading": _normalize_text(item.get("heading")),
		"show_heading": _as_bool(item.get("show_heading"), True),
		"show_matrix": _as_bool(item.get("show_matrix"), True),
		"span_full_width": _as_bool(item.get("span_full_width"), True),
		"x": _as_float(item.get("x")),
		"y": _as_float(item.get("y")),
		"width": max(_as_float(item.get("width"), 420.0), 0.0),
		"rows": rows,
		"cols": cols,
		"row_height": row_height,
		"heading_height": heading_height,
		"style": _parse_json(item.get("style"), {}) if isinstance(item.get("style"), (str, dict)) else {},
	}
	matrix["height"] = _matrix_height(matrix)
	matrix["cells"] = _build_matrix_cells(rows, cols, item.get("cells") or [])
	matrix["id"] = matrix["id"] or f"matrix_{rows}x{cols}"
	return matrix


def _normalize_layout(layout_json):
	layout = _parse_json(layout_json, {})
	items = []
	for item in layout.get("items", []):
		if not isinstance(item, dict):
			continue

		if item.get("kind") == "matrix" or isinstance(item.get("cells"), list):
			items.append(_normalize_matrix_item(item))
			continue

		fieldname = _normalize_text(item.get("fieldname"))
		if not fieldname:
			continue

		items.append(_normalize_field_item(item))

	return {"items": items}


def _normalize_page_value(value, fallback):
	return _normalize_text(value, fallback)


def _serialize_template_snapshot(template_doc):
	return {
		"name": template_doc.name,
		"form_name": template_doc.form_name,
		"description": template_doc.description,
		"form_type": template_doc.form_type,
		"target_doctype": template_doc.target_doctype,
		"is_active": template_doc.is_active,
		"schema": _parse_json(template_doc.schema_json, {}),
	}


def _get_template_doc(template_name, permission="read"):
	doc = frappe.get_doc(TEMPLATE_DOCTYPE, template_name)
	doc.check_permission(permission)
	return doc


def _get_submission_doc(submission_name, permission="read"):
	doc = frappe.get_doc(SUBMISSION_DOCTYPE, submission_name)
	doc.check_permission(permission)
	return doc


def _serialize_doc(doc):
	layout = _parse_json(doc.layout_json, {"items": []})
	snapshot = _parse_json(doc.template_snapshot_json, {})
	return {
		"name": doc.name,
		"format_name": doc.format_name,
		"dynamic_form_template": doc.dynamic_form_template,
		"is_default": int(doc.is_default or 0),
		"is_active": int(doc.is_active or 0),
		"page_width": doc.page_width,
		"page_height": doc.page_height,
		"margin_top": doc.margin_top,
		"margin_right": doc.margin_right,
		"margin_bottom": doc.margin_bottom,
		"margin_left": doc.margin_left,
		"layout": layout,
		"template_snapshot": snapshot,
		"preview_image": getattr(doc, "preview_image", "") or "",
	}


@dataclass
class DynamicPrintFormatService:
	template_name: str | None = None

	def normalize_document(self, payload):
		template_name = _normalize_text(payload.get("dynamic_form_template"))
		if not template_name:
			frappe.throw(_("Dynamic form template is required."))

		template_doc = _get_template_doc(template_name, permission="read")
		format_name = _normalize_text(payload.get("format_name"))
		if not format_name:
			frappe.throw(_("Format name is required."))

		layout = _normalize_layout(payload.get("layout_json"))
		return {
			"format_name": format_name,
			"dynamic_form_template": template_name,
			"is_default": 1 if _as_bool(payload.get("is_default"), False) else 0,
			"is_active": 1 if _as_bool(payload.get("is_active"), True) else 0,
			"page_width": _normalize_page_value(payload.get("page_width"), DEFAULT_PAGE["page_width"]),
			"page_height": _normalize_page_value(payload.get("page_height"), DEFAULT_PAGE["page_height"]),
			"margin_top": _normalize_page_value(payload.get("margin_top"), DEFAULT_PAGE["margin_top"]),
			"margin_right": _normalize_page_value(payload.get("margin_right"), DEFAULT_PAGE["margin_right"]),
			"margin_bottom": _normalize_page_value(payload.get("margin_bottom"), DEFAULT_PAGE["margin_bottom"]),
			"margin_left": _normalize_page_value(payload.get("margin_left"), DEFAULT_PAGE["margin_left"]),
			"layout_json": json.dumps(layout, ensure_ascii=False, indent=2),
			"template_snapshot_json": json.dumps(_serialize_template_snapshot(template_doc), ensure_ascii=False, indent=2),
		}

	def list_for_template(self):
		template_name = _normalize_text(self.template_name)
		if not template_name:
			frappe.throw(_("Dynamic form template is required."))

		_get_template_doc(template_name, permission="read")
		formats = frappe.get_all(
			PRINT_FORMAT_DOCTYPE,
			filters={
				"dynamic_form_template": template_name,
			},
			fields=[
				"name",
				"format_name",
				"dynamic_form_template",
				"is_default",
				"is_active",
				"page_width",
				"page_height",
			],
			order_by="is_default desc, modified desc",
		)
		return formats

	def get(self, format_name):
		format_name = _normalize_text(format_name)
		if not format_name:
			frappe.throw(_("Print format is required."))

		doc = frappe.get_doc(PRINT_FORMAT_DOCTYPE, format_name)
		doc.check_permission("read")
		return _serialize_doc(doc)

	def save(self, payload):
		doc_values = {
			"doctype": PRINT_FORMAT_DOCTYPE,
			**self.normalize_document(payload),
		}
		existing_name = _normalize_text(payload.get("name") or payload.get("docname"))
		target_name = existing_name or doc_values["format_name"]

		existing = frappe.db.exists(PRINT_FORMAT_DOCTYPE, target_name)
		if existing:
			doc = frappe.get_doc(PRINT_FORMAT_DOCTYPE, target_name)
			doc.check_permission("write")
			for key, value in doc_values.items():
				if key == "doctype":
					continue
				setattr(doc, key, value)
			doc.save()
			if doc.name != doc_values["format_name"]:
				renamed = frappe.rename_doc(PRINT_FORMAT_DOCTYPE, doc.name, doc_values["format_name"], force=True)
				doc = frappe.get_doc(PRINT_FORMAT_DOCTYPE, renamed)
		else:
			doc = frappe.get_doc(doc_values)
			doc.insert()

		if doc.is_default:
			self._unset_other_defaults(doc.name, doc.dynamic_form_template)

		frappe.db.commit()
		return _serialize_doc(doc)

	def get_render_context(self, format_name, submission_name):
		doc = frappe.get_doc(PRINT_FORMAT_DOCTYPE, _normalize_text(format_name))
		doc.check_permission("read")

		submission = _get_submission_doc(submission_name, permission="read")
		if submission.form_template != doc.dynamic_form_template:
			frappe.throw(_("The selected submission does not belong to this template."))

		template_doc = _get_template_doc(doc.dynamic_form_template, permission="read")
		return {
			"print_format": _serialize_doc(doc),
			"template": _serialize_template_snapshot(template_doc),
			"submission": {
				"name": submission.name,
				"form_template": submission.form_template,
				"data": _parse_json(submission.data_json, {}),
				"status": submission.status,
				"submitted_on": str(submission.submitted_on) if submission.submitted_on else "",
				"owner": submission.owner,
				"reference_doctype": submission.reference_doctype or "",
				"reference_name": submission.reference_name or "",
			},
		}

	def _unset_other_defaults(self, current_name, template_name):
		others = frappe.get_all(
			PRINT_FORMAT_DOCTYPE,
			filters={
				"dynamic_form_template": template_name,
				"is_default": 1,
				"name": ["!=", current_name],
			},
			pluck="name",
		)
		for name in others:
			frappe.db.set_value(PRINT_FORMAT_DOCTYPE, name, "is_default", 0)
