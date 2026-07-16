"""Create a real DocType from a Dynamic Form Template."""

from __future__ import annotations

import json
import re
from copy import deepcopy

import frappe
from frappe import _
from frappe.utils import cint, escape_html

DEFAULT_MODULE = "Ampower Form Builder"
MAX_DOCTYPE_NAME_LENGTH = 61
SQL_KEYWORDS = {
	"select", "insert", "update", "delete", "drop", "table", "from", "where", "join",
	"group", "order", "limit", "by", "and", "or", "into", "create", "alter", "index",
	"primary", "key", "constraint", "grant", "revoke", "union", "having", "distinct",
}

LAYOUT_FIELD_TYPES = {"Section Break", "Tab Break", "Column Break", "HTML", "Heading"}
TABLE_FIELD_TYPES = {"Table", "Mixed Table"}


def _normalize_text(value):
	return (value or "").strip()


def _sanitize_doctype_name(value, fallback="Form"):
	"""Return a Frappe-safe DocType name."""
	name = _normalize_text(value)
	name = re.sub(r"[^A-Za-z0-9 _-]+", " ", name)
	name = re.sub(r"\s+", " ", name).strip(" _-")
	name = re.sub(r"^[^A-Za-z]+", "", name)
	if not name:
		name = _normalize_text(fallback) or "Form"
	if len(name) > MAX_DOCTYPE_NAME_LENGTH:
		name = name[:MAX_DOCTYPE_NAME_LENGTH].rstrip(" -_")
	return name or "Form"


def _sanitize_fieldname(value, fallback="field"):
	name = _normalize_text(value).lower()
	name = re.sub(r"['\"]", "", name)
	name = re.sub(r"[^a-z0-9]+", "_", name)
	name = re.sub(r"_+", "_", name).strip("_")
	if not name:
		name = _normalize_text(fallback).lower()
		name = re.sub(r"['\"]", "", name)
		name = re.sub(r"[^a-z0-9]+", "_", name)
		name = re.sub(r"_+", "_", name).strip("_")
	if not name or not re.match(r"^[a-z]", name):
		name = f"field_{name}" if name else "field"
	if name in SQL_KEYWORDS:
		name = f"{name}_field"
	return name.rstrip("_") or "field"


def _unique_fieldname(base_name, existing_names=None, fallback="field"):
	if existing_names is None:
		existing_names = set()
	elif not isinstance(existing_names, set):
		existing_names = set(existing_names)
	candidate = _sanitize_fieldname(base_name, fallback=fallback)
	counter = 2

	while candidate in existing_names:
		suffix = f"_{counter}"
		trimmed = candidate
		if len(trimmed) + len(suffix) > 140:
			trimmed = trimmed[: 140 - len(suffix)].rstrip(" _")
		candidate = _sanitize_fieldname(f"{trimmed}{suffix}", fallback=fallback)
		counter += 1

	existing_names.add(candidate)
	return candidate


def _as_bool(value):
	return 1 if cint(value) else 0


def _full_permissions():
	return [
		{
			"role": "System Manager",
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"submit": 0,
			"cancel": 0,
			"print": 1,
			"email": 1,
			"report": 1,
			"share": 1,
		},
	]


def _unique_doctype_name(base_name, existing_names=None, fallback="Form"):
	existing_names = set(existing_names or [])
	candidate = _sanitize_doctype_name(base_name, fallback=fallback)
	counter = 2

	while candidate in existing_names or _doctype_exists(candidate):
		suffix = f" {counter}"
		trimmed = candidate
		if len(trimmed) + len(suffix) > MAX_DOCTYPE_NAME_LENGTH:
			trimmed = trimmed[: MAX_DOCTYPE_NAME_LENGTH - len(suffix)].rstrip(" -_")
		candidate = _sanitize_doctype_name(f"{trimmed}{suffix}", fallback=fallback)
		counter += 1

	return candidate


def _doctype_exists(doctype_name):
	try:
		return bool(frappe.db.exists("DocType", doctype_name))
	except RuntimeError:
		return False


def _ensure_system_manager():
	if "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError(_("Only System Managers can create DocTypes from templates."))


def _field_label(field, fallback=""):
	return _normalize_text(
		field.get("label")
		or field.get("field_label")
		or field.get("section_label")
		or fallback
	)


def _field_fieldname(field, fallback="field"):
	return _sanitize_fieldname(field.get("fieldname") or field.get("field_name") or field.get("section_key") or fallback, fallback=fallback)


def _fieldtype(field):
	return _normalize_text(field.get("fieldtype") or field.get("field_type") or "Data")


def _doctype_fieldtype(fieldtype):
	return "Float" if fieldtype == "Number" else fieldtype


def _table_config(field):
	options = field.get("options")
	if isinstance(options, str) and options:
		try:
			options = json.loads(options)
		except Exception:
			options = {}
	elif not isinstance(options, dict):
		options = {}

	columns = field.get("table_columns") or options.get("columns") or options.get("table_columns") or []
	rows = field.get("table_rows") or options.get("rows") or []

	return {
		"columns": columns if isinstance(columns, list) else [],
		"rows": rows if isinstance(rows, list) else [],
		"table_row_title": _normalize_text(
			field.get("table_row_title")
			or options.get("table_row_title")
			or options.get("row_title")
			or ""
		),
		"image_column": _normalize_text(field.get("image_column") or options.get("image_column") or ""),
	}


class BuilderDocTypeCreator:
	"""Build and create a DocType from a saved builder template."""

	def __init__(self, template_doc, doctype_name=None, module=DEFAULT_MODULE):
		self.template_doc = template_doc
		self.module = _normalize_text(module) or DEFAULT_MODULE
		self.doctype_name = _unique_doctype_name(
			doctype_name or getattr(template_doc, "form_name", "") or template_doc.name
		)
		self.schema = self._load_schema()
		self._blueprint = None

	def build_blueprint(self):
		"""Return the parent DocType payload and any child table doctypes."""
		if self._blueprint is not None:
			return deepcopy(self._blueprint)

		parent_fields = []
		child_doctypes = []
		seen_parent_names = set()
		seen_child_names = set()
		has_concrete_field = False

		for index, field in enumerate(self._iter_schema_fields()):
			field_payload, child_payload = self._build_field_payload(field, index, seen_parent_names, seen_child_names)
			if field_payload:
				parent_fields.append(field_payload)
				if field_payload["fieldtype"] not in LAYOUT_FIELD_TYPES:
					has_concrete_field = True
			if child_payload:
				child_doctypes.append(child_payload)
				has_concrete_field = True

		if not has_concrete_field:
			frappe.throw(_("The template does not contain any fields that can be converted into a DocType."))

		self._blueprint = {
			"doctype": {
				"doctype": "DocType",
				"name": self.doctype_name,
				"module": self.module,
				"custom": 1,
				"fields": parent_fields,
				"permissions": _full_permissions(),
			},
			"child_doctypes": child_doctypes,
		}
		return deepcopy(self._blueprint)

	def create(self):
		"""Persist the generated DocType and any child tables."""
		_ensure_system_manager()
		blueprint = self.build_blueprint()
		all_names = [blueprint["doctype"]["name"], *[child["doctype"]["name"] for child in blueprint["child_doctypes"]]]

		for doctype_name in all_names:
			if _doctype_exists(doctype_name):
				frappe.throw(_("DocType {0} already exists.").format(frappe.bold(doctype_name)))

		try:
			created_child_doctypes = []
			for child_blueprint in blueprint["child_doctypes"]:
				child_doc = self._insert_doctype(child_blueprint["doctype"])
				created_child_doctypes.append(child_doc.name)

			parent_doc = self._insert_doctype(blueprint["doctype"])
			return {
				"doctype_name": parent_doc.name,
				"template_name": self.template_doc.name,
				"child_doctypes": created_child_doctypes,
			}
		except Exception:
			self._cleanup_created_doctypes(all_names)
			raise

	def _load_schema(self):
		schema = getattr(self.template_doc, "schema_json", {}) or {}
		if isinstance(schema, str):
			try:
				schema = json.loads(schema)
			except Exception as exc:
				frappe.throw(_("Template schema is invalid: {0}").format(str(exc)))
		if not isinstance(schema, dict):
			return {}
		return schema

	def _iter_schema_fields(self):
		fields = self.schema.get("fields")
		if isinstance(fields, list) and fields:
			for field in fields:
				yield self._normalize_field(field)
			return

		for section in self.schema.get("sections", []) or []:
			section = dict(section or {})
			section_type = _normalize_text(section.get("item_type") or section.get("type") or "Section Break") or "Section Break"
			yield self._normalize_field(
				{
					"fieldtype": section_type,
					"fieldname": section.get("section_key") or section.get("id"),
					"label": section.get("section_label") or section.get("label") or "",
				}
			)

			for column_index, column in enumerate(section.get("columns", []) or []):
				if column_index > 0:
					yield self._normalize_field(
						{
							"fieldtype": "Column Break",
							"label": "Column Break",
							"fieldname": f"{section.get('section_key') or section.get('id')}_column_{column_index + 1}",
						}
					)

				for field in column.get("items", []) or []:
					yield self._normalize_field(field)

	def _normalize_field(self, field):
		field = dict(field or {})
		fieldtype = _fieldtype(field)
		field["fieldtype"] = fieldtype
		field["field_type"] = fieldtype

		fieldname = _field_fieldname(field, fallback=_field_label(field, "field"))
		if fieldname:
			field["fieldname"] = fieldname
			field["field_name"] = fieldname

		label = _field_label(field, fieldname or "Field")
		if label:
			field["label"] = label
			field["field_label"] = label

		if fieldtype in {"Link", "Dynamic Link"}:
			field["options"] = _normalize_text(field.get("options") or field.get("_doctype") or "")
		elif fieldtype in TABLE_FIELD_TYPES:
			config = _table_config(field)
			field["table_columns"] = config["columns"]
			field["table_rows"] = config["rows"]
			field["table_row_title"] = config["table_row_title"]
			field["image_column"] = config["image_column"]
			field["options"] = json.dumps(config, sort_keys=True)

		return field

	def _build_field_payload(self, field, sequence, seen_parent_names, seen_child_names):
		fieldtype = _fieldtype(field)
		if fieldtype in {"Section Break", "Tab Break", "Column Break"}:
			return self._build_layout_payload(fieldtype, field, seen_parent_names), None

		if fieldtype == "HTML":
			return self._build_html_payload(field), None

		if fieldtype == "Heading":
			return self._build_heading_payload(field), None

		if fieldtype in TABLE_FIELD_TYPES:
			child_blueprint = self._build_child_doctype(field, sequence, seen_parent_names, seen_child_names)
			return child_blueprint["parent_field"], child_blueprint

		return self._build_standard_payload(field, seen_parent_names), None

	def _build_layout_payload(self, fieldtype, field, seen_parent_names):
		label = _field_label(field, "")
		fallback = label or fieldtype.lower().replace(" ", "_")
		payload = {
			"fieldtype": fieldtype,
			"fieldname": _unique_fieldname(_field_fieldname(field, fallback=fallback), existing_names=seen_parent_names, fallback=fallback),
		}
		if fieldtype in {"Section Break", "Tab Break"}:
			if label:
				payload["label"] = label
		return payload

	def _build_html_payload(self, field):
		payload = {"fieldtype": "HTML"}
		content = _normalize_text(
			field.get("options")
			or field.get("default")
			or field.get("description")
			or field.get("label")
			or ""
		)
		if content:
			payload["options"] = content
		return payload

	def _build_heading_payload(self, field):
		label = _field_label(field, "")
		payload = {"fieldtype": "HTML"}
		if label:
			payload["options"] = f"<h4>{escape_html(label)}</h4>"
		return payload

	def _build_standard_payload(self, field, seen_parent_names):
		fieldtype = _fieldtype(field)
		doctype_fieldtype = _doctype_fieldtype(fieldtype)
		fieldname = _unique_fieldname(_field_fieldname(field), existing_names=seen_parent_names, fallback=_field_label(field, fieldtype or "field"))
		if not fieldname:
			frappe.throw(_("Field {0} is missing a fieldname.").format(frappe.bold(_field_label(field, fieldtype))))

		payload = {
			"fieldtype": doctype_fieldtype,
			"fieldname": fieldname,
			"label": _field_label(field, fieldname),
			"reqd": _as_bool(field.get("reqd")),
			"read_only": _as_bool(field.get("read_only")),
			"hidden": _as_bool(field.get("hidden")),
			"description": _normalize_text(field.get("description") or ""),
			"placeholder": _normalize_text(field.get("placeholder") or ""),
			"default": field.get("default") if field.get("default") is not None else "",
			"depends_on": _normalize_text(field.get("depends_on") or ""),
			"fetch_from": _normalize_text(field.get("fetch_from") or ""),
			"precision": field.get("precision") if field.get("precision") not in (None, "") else "",
		}

		options = _normalize_text(field.get("options") or field.get("_doctype") or "")
		if fieldtype == "Link":
			if not options:
				frappe.throw(_("Field {0} must define a DocType option.").format(frappe.bold(payload["label"])))
			payload["options"] = options
		elif fieldtype == "Dynamic Link":
			if not options:
				frappe.throw(_("Field {0} must define a source field.").format(frappe.bold(payload["label"])))
			payload["options"] = options
		elif fieldtype in {"Select", "Radio"}:
			if not options:
				frappe.throw(_("Field {0} must define options.").format(frappe.bold(payload["label"])))
			payload["options"] = options
		else:
			if options:
				payload["options"] = options

		return payload

	def _build_child_doctype(self, field, sequence, seen_parent_names, seen_child_names):
		fieldname = _field_fieldname(field)
		child_base_name = f"{self.doctype_name} {_field_label(field, fieldname or 'Items')}"
		child_name = _unique_doctype_name(child_base_name, existing_names=seen_child_names)
		seen_child_names.add(child_name)

		columns = _table_config(field)["columns"]
		if not columns:
			frappe.throw(_("Table field {0} must define columns.").format(frappe.bold(_field_label(field, fieldname))))

		seen_child_fieldnames = set()
		child_fields = [self._build_child_field(column, index, seen_child_fieldnames) for index, column in enumerate(columns)]
		if field.get("fieldtype") == "Mixed Table" and not child_fields:
			frappe.throw(_("Mixed Table field {0} must define columns.").format(frappe.bold(_field_label(field, fieldname))))

		child_doctype = {
			"doctype": "DocType",
			"name": child_name,
			"module": self.module,
			"custom": 1,
			"istable": 1,
			"fields": child_fields,
			"permissions": _full_permissions(),
		}

		parent_field = {
			"fieldtype": "Table",
			"fieldname": _unique_fieldname(fieldname, existing_names=seen_parent_names, fallback=_field_label(field, fieldname or "table")),
			"label": _field_label(field, fieldname),
			"options": child_name,
			"reqd": _as_bool(field.get("reqd")),
			"read_only": _as_bool(field.get("read_only")),
			"hidden": _as_bool(field.get("hidden")),
			"description": _normalize_text(field.get("description") or ""),
		}

		return {
			"doctype": child_doctype,
			"parent_field": parent_field,
		}

	def _build_child_field(self, column, index, seen_child_fieldnames):
		column = self._normalize_field(column)
		fieldtype = _fieldtype(column)
		doctype_fieldtype = _doctype_fieldtype(fieldtype)
		fieldname = _unique_fieldname(_field_fieldname(column, fallback=f"column_{index + 1}"), existing_names=seen_child_fieldnames, fallback=f"column_{index + 1}")
		if not fieldname:
			frappe.throw(_("Table column {0} is missing a fieldname.").format(index + 1))

		payload = {
			"fieldtype": doctype_fieldtype,
			"fieldname": fieldname,
			"label": _field_label(column, fieldname),
			"reqd": _as_bool(column.get("reqd")),
			"read_only": _as_bool(column.get("read_only")),
			"hidden": _as_bool(column.get("hidden")),
			"description": _normalize_text(column.get("description") or ""),
			"placeholder": _normalize_text(column.get("placeholder") or ""),
			"default": column.get("default") if column.get("default") is not None else "",
			"depends_on": _normalize_text(column.get("depends_on") or ""),
			"fetch_from": _normalize_text(column.get("fetch_from") or ""),
			"precision": column.get("precision") if column.get("precision") not in (None, "") else "",
			"in_list_view": 1,
		}

		options = _normalize_text(column.get("options") or column.get("_doctype") or "")
		if fieldtype == "Link":
			if not options:
				frappe.throw(_("Table column {0} must define a DocType option.").format(frappe.bold(payload["label"])))
			payload["options"] = options
		elif fieldtype in {"Select", "Radio"}:
			if not options:
				frappe.throw(_("Table column {0} must define options.").format(frappe.bold(payload["label"])))
			payload["options"] = options
		elif options:
			payload["options"] = options

		return payload

	def _insert_doctype(self, doctype_payload):
		doc = frappe.get_doc(doctype_payload)
		doc.flags.ignore_permissions = False
		doc.insert()
		return doc

	def _cleanup_created_doctypes(self, doctype_names):
		for doctype_name in reversed(doctype_names):
			if not frappe.db.exists("DocType", doctype_name):
				continue
			try:
				frappe.delete_doc(
					"DocType",
					doctype_name,
					force=True,
					ignore_permissions=True,
				)
			except Exception:
				frappe.log_error(
					title=_("Ampower Form Builder DocType Cleanup Error"),
					message=frappe.get_traceback(),
				)


def create_doctype_from_template(template_doc, doctype_name=None, module=DEFAULT_MODULE):
	"""Create a new custom DocType from a saved template document."""
	return BuilderDocTypeCreator(template_doc, doctype_name=doctype_name, module=module).create()
