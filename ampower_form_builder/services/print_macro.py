import base64
import json
import mimetypes

import frappe
from frappe.utils.file_manager import get_file

SUBMISSION_DOCTYPE = "Dynamic Form Submission"
SUBMISSION_FIELDNAME = "afb_integration_submission"
FORM_TEMPLATE_DOCTYPE = "Dynamic Form Template"

def safe_json_load(value):
	if not value:
		return {}

	if isinstance(value, dict):
		return value

	if isinstance(value, str):
		try:
			return json.loads(value)
		except ValueError:
			return {}

	return {}


def build_template_field_map(schema):
	field_map = {}

	def add_fields(fields):
		for field in fields or []:
			if not isinstance(field, dict):
				continue

			fieldname = field.get("fieldname")
			if fieldname:
				field_map.setdefault(fieldname, field)

			for column in field.get("columns") or []:
				if isinstance(column, dict) and column.get("fieldname"):
					field_map.setdefault(column.get("fieldname"), column)

	if isinstance(schema, dict):
		add_fields(schema.get("fields"))

		for section in schema.get("sections") or []:
			if not isinstance(section, dict):
				continue

			for column in section.get("columns") or []:
				if not isinstance(column, dict):
					continue
				add_fields(column.get("items") or column.get("fields"))
		return field_map

	for section in schema or []:
		if not isinstance(section, dict):
			continue
		add_fields(section.get("fields"))
		for column in section.get("columns") or []:
			if isinstance(column, dict):
				add_fields(column.get("fields") or column.get("items"))

	return field_map


def get_template_field_map(template_name, schema_json=None):
    if not template_name:
        return {}

    try:
        from ampower_form_builder.api import get_form_schema

        schema = (get_form_schema(template_name) or {}).get("schema")
        if schema:
            return build_template_field_map(schema)
    except Exception:
        LOGGER.warning(
            "Unable to load cached Ampower template schema | template=%s",
            template_name,
            exc_info=True,
        )


def build_template_layout(schema):
	layout = {"sections": []}

	def get_fieldname_list(fields):
		fieldnames = []
		for field in fields or []:
			if not isinstance(field, dict):
				continue

			fieldname = field.get("fieldname")
			if fieldname:
				fieldnames.append(fieldname)

		return fieldnames

	def add_section(section_label="", columns=None):
		section_columns = []
		for index, column in enumerate(columns or [], start=1):
			if not isinstance(column, dict):
				continue

			fieldnames = get_fieldname_list(column.get("items") or column.get("fields"))
			if fieldnames:
				section_columns.append(
					{"label": column.get("label") or "", "index": index, "fieldnames": fieldnames}
				)

		if section_columns:
			layout["sections"].append({"label": section_label or "", "columns": section_columns})

	def add_root_fields(fields):
		default_fields = []

		for field in fields or []:
			if not isinstance(field, dict):
				continue

			if field.get("columns"):
				add_section(field.get("label") or "", field.get("columns"))
				continue

			fieldname = field.get("fieldname")
			if fieldname:
				default_fields.append(fieldname)

		if default_fields:
			layout["sections"].append(
				{"label": "", "columns": [{"label": "", "index": 1, "fieldnames": default_fields}]}
			)

	if isinstance(schema, dict):
		sections = schema.get("sections") or []

		if sections:
			for section in sections:
				if not isinstance(section, dict):
					continue
				add_section(section.get("label") or section.get("title") or "", section.get("columns"))
		else:
			add_root_fields(schema.get("fields"))

		return layout

	for section in schema or []:
		if not isinstance(section, dict):
			continue

		if section.get("columns"):
			add_section(section.get("label") or section.get("title") or "", section.get("columns"))
			continue

		fieldnames = get_fieldname_list(section.get("fields"))
		if fieldnames:
			layout["sections"].append(
				{"label": section.get("label") or "", "columns": [{"label": "", "index": 1, "fieldnames": fieldnames}]}
			)

	return layout



def get_template_layout(template_name, schema_json=None):
    if not template_name:
        return {"sections": []}

    try:
        from ampower_form_builder.api import get_form_schema

        schema = (get_form_schema(template_name) or {}).get("schema")
        if schema:
            return build_template_layout(schema)
    except Exception:
        LOGGER.warning(
            "Unable to load cached Ampower template layout | template=%s",
            template_name,
            exc_info=True,
        )

def format_print_value(value):
	if value in (None, "", []):
		return ""

	if isinstance(value, bool):
		return "Yes" if value else "No"

	if isinstance(value, int | float):
		return value

	if isinstance(value, list):
		if all(not isinstance(item, dict | list) for item in value):
			return ", ".join(str(item) for item in value if item not in (None, ""))
		return json.dumps(value, ensure_ascii=True)

	if isinstance(value, dict):
		return json.dumps(value, ensure_ascii=True)

	return str(value)


def build_printable_attachment_data(value, field_meta):
	file_details = get_printable_file_details(value)
	file_url = file_details.get("file_url", "")
	file_name = file_details.get("file_name", "")
	fieldtype = field_meta.get("fieldtype") or ""
	return {
		"type": "attachment_image" if fieldtype in {"Attach Image", "Image", "Signature"} else "attachment",
		"fieldname": field_meta.get("fieldname"),
		"label": field_meta.get("label") or field_meta.get("fieldname"),
		"fieldtype": fieldtype,
		"file_url": file_url,
		"file_name": file_name,
		"value": file_url,
	}


def get_printable_file_details(value):
	if isinstance(value, dict):
		file_url = value.get("file_url") or value.get("url") or value.get("value") or ""
		file_name = value.get("file_name") or value.get("name") or file_url.rsplit("/", 1)[-1]
	else:
		file_url = str(value or "")
		file_name = file_url.rsplit("/", 1)[-1] if file_url else ""

	if file_url:
		file_record = frappe.get_all(
			"File",
			filters={"file_url": file_url},
			fields=["name", "file_url", "file_name", "is_private"],
			limit=1,
			ignore_permissions=True,
		)
		if file_record:
			file_record = file_record[0]
			file_url = file_record.get("file_url") or file_url
			file_name = file_record.get("file_name") or file_name
			if file_record.get("is_private"):
				file_url = build_private_file_data_uri(file_url, file_name) or file_url

	return {"file_url": file_url, "file_name": file_name}


def build_private_file_data_uri(file_url, file_name=None):
	mime_type = mimetypes.guess_type(file_name or file_url)[0] or ""
	if not mime_type.startswith("image/"):
		return None

	try:
		_, content = get_file(file_url)
	except Exception:
		LOGGER.warning("Unable to inline private printable file | file_url=%s", file_url, exc_info=True)
		return None

	if isinstance(content, str):
		content = content.encode("utf-8")

	if not content:
		return None

	return f"data:{mime_type};base64,{base64.b64encode(content).decode()}"


def is_image_fieldtype(fieldtype):
	return (fieldtype or "") in {"Attach Image", "Image", "Signature"}


def extract_file_url(value):
	return get_printable_file_details(value).get("file_url", "")


def get_table_config(field_meta):
	if not field_meta or (field_meta.get("fieldtype") not in {"Table", "Mixed Table"}):
		return {"columns": [], "rows": [], "table_row_title": "", "mode": "table", "image_column": "1"}

	options = safe_json_load(field_meta.get("options"))
	image_column = str(options.get("image_column") or field_meta.get("image_column") or "1").strip()
	if image_column not in {"1", "2"}:
		image_column = "1"

	return {
		"columns": options.get("columns") or field_meta.get("table_columns") or [],
		"rows": options.get("rows") or field_meta.get("table_rows") or [],
		"table_row_title": field_meta.get("table_row_title")
		or options.get("table_row_title")
		or options.get("row_title")
		or "",
		"mode": options.get("mode") or ("mixed" if field_meta.get("fieldtype") == "Mixed Table" else "table"),
		"image_column": image_column,
	}


def build_printable_table_data(value, field_meta):
	table_config = get_table_config(field_meta)
	column_defs = table_config["columns"]
	row_defs = table_config["rows"]
	parsed_value = safe_json_load(value) if isinstance(value, str) else value
	rows = parsed_value if isinstance(parsed_value, list) else []
	fieldtype = field_meta.get("fieldtype") or ""
	is_mixed = fieldtype == "Mixed Table"

	printable_columns = [
		{
			"fieldname": column.get("fieldname"),
			"label": column.get("label") or column.get("fieldname"),
			"fieldtype": column.get("fieldtype") or "Data",
			"is_image": is_image_fieldtype(column.get("fieldtype")),
		}
		for column in column_defs
		if column.get("fieldname")
	]

	has_image_columns = any(column["is_image"] for column in printable_columns)
	data_rows = []

	for index, row in enumerate(rows):
		row = row or {}
		row_definition = row_defs[index] if index < len(row_defs) else {}
		row_label = row_definition.get("label") or str(index + 1)
		row_key = row_definition.get("key") or row_label
		data_row = {"row_name": row_label, "row_label": row_label, "row_key": row_key}

		for column in printable_columns:
			cell_value = row.get(column["fieldname"])
			data_row[column["fieldname"]] = (
				extract_file_url(cell_value) if column["is_image"] else format_print_value(cell_value)
			)
		data_rows.append(data_row)

	headers = [
		{
			"key": column["fieldname"],
			"label": column["label"],
			"fieldtype": column["fieldtype"],
			"is_image": column["is_image"],
		}
		for column in printable_columns
	]

	if fieldtype == "Mixed Table":
		headers = [
			{"key": "row_name", "label": table_config["table_row_title"] or "Parameter", "fieldtype": "Data"},
			*headers,
		]

	result = {
		"type": "image_table" if has_image_columns else "table",
		"fieldname": field_meta.get("fieldname"),
		"label": field_meta.get("label") or field_meta.get("fieldname"),
		"fieldtype": fieldtype,
		"mode": table_config["mode"],
		"headers": headers,
		"data": data_rows,
	}

	if has_image_columns:
		result["image_column"] = table_config["image_column"]

	if is_mixed:
		result["table_row_title"] = table_config["table_row_title"] or "Parameter"

	return result


def build_printable_item(fieldname, value, field_meta=None):
	field_meta = field_meta or {}
	fieldtype = field_meta.get("fieldtype")

	if fieldtype in {"Table", "Mixed Table"}:
		return build_printable_table_data(value, field_meta)

	if fieldtype in {"Attach", "Attach Image", "Image", "Signature"}:
		attachment_data = build_printable_attachment_data(value, field_meta)
		return attachment_data if attachment_data.get("file_url") else None

	formatted_value = format_print_value(value)
	if formatted_value in ("", None):
		return None

	return {
		"fieldname": fieldname,
		"label": field_meta.get("label", fieldname.replace("_", " ").title()),
		"fieldtype": fieldtype or "",
		"type": "field",
		"value": formatted_value,
	}



def get_submission_context(results):
	
	submission_names = list(
		dict.fromkeys(row.get(SUBMISSION_FIELDNAME) for row in results if row.get(SUBMISSION_FIELDNAME))
	)
	if not submission_names:
		return {}, {}, {}

	try:
		submission = frappe.qb.DocType(SUBMISSION_DOCTYPE)
		template = frappe.qb.DocType(FORM_TEMPLATE_DOCTYPE)
		submission_rows = (
			frappe.qb.from_(submission)
			.left_join(template)
			.on(template.name == submission.form_template)
			.select(
				submission.name.as_("name"),
				submission.form_template.as_("form_template"),
				submission.data_json.as_("data_json"),
				template.schema_json.as_("schema_json"),
			)
			.where(submission.name.isin(submission_names))
		).run(as_dict=True)
	except Exception:
		LOGGER.error(
			"Failed to build submission context | submissions=%s | count=%s",
			submission_names[:10],
			len(submission_names),
			exc_info=True,
		)
		raise
	submission_map = {}
	template_field_maps = {}
	template_layouts = {}

	for row in submission_rows:
		row._parsed_data = safe_json_load(row.data_json)
		submission_map[row.name] = row

		if row.form_template and row.form_template not in template_field_maps:
			template_field_maps[row.form_template] = get_template_field_map(
				row.form_template, row.schema_json
			)
			template_layouts[row.form_template] = get_template_layout(row.form_template, row.schema_json)

	return submission_map, template_field_maps, template_layouts


def get_printable_data(doc, submission_fieldname=SUBMISSION_FIELDNAME):
	if not doc or not getattr(doc, "name", None) or doc.is_new():
		return {}

	submission_name = doc.get(submission_fieldname)
	if not submission_name:
		return {}

	submission_map, template_field_maps, template_layouts = get_submission_context(
		[{submission_fieldname: submission_name}]
	)
	submission = submission_map.get(submission_name)

	if not submission:
		return {}

	field_map = template_field_maps.get(submission.form_template, {})
	template_layout = template_layouts.get(submission.form_template, {})
	submission_data = getattr(submission, "_parsed_data", {}) or {}

	return {
		"submission_name": submission.name,
		"form_template": submission.form_template,
		"layout": build_printable_submission_data(
			submission_data, field_map, template_layout=template_layout, include_layout=True
		),
	}


def build_printable_submission_data(data, field_map=None, template_layout=None, include_layout=False):
	field_map = field_map or {}
	printable_rows = []
	layout_sections = []
	used_fieldnames = set()

	def append_item(target, fieldname):
		item = build_printable_item(fieldname, (data or {}).get(fieldname), field_map.get(fieldname, {}))
		if item:
			target.append(item)
			used_fieldnames.add(fieldname)

	for section in (template_layout or {}).get("sections") or []:
		section_columns = []

		for column in section.get("columns") or []:
			column_items = []
			for fieldname in column.get("fieldnames") or []:
				append_item(column_items, fieldname)

			if column_items:
				section_columns.append(
					{
						"label": column.get("label") or "",
						"index": column.get("index") or 1,
						"items": column_items,
					}
				)
				printable_rows.extend(column_items)

		if section_columns:
			layout_sections.append({"label": section.get("label") or "", "columns": section_columns})

	for fieldname in (data or {}):
		if fieldname in used_fieldnames:
			continue

		extra_items = []
		append_item(extra_items, fieldname)
		if extra_items:
			printable_rows.extend(extra_items)

	if include_layout:
		if printable_rows and not layout_sections:
			layout_sections = [{"label": "", "columns": [{"label": "", "index": 1, "items": printable_rows}]}]
		return {"items": printable_rows, "sections": layout_sections}

	return printable_rows