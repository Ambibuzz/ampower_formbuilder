# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

"""Whitelisted API methods for the Ampower Form Builder.

These methods power the Form Builder and Form Viewer pages,
providing CRUD operations for templates and submissions while
keeping the builder schema in JSON until an explicit DocType export is requested.
"""

import json
import re

import frappe
from frappe import _
from frappe.exceptions import ValidationError

from ampower_form_builder.services.ai_form_builder import (
	get_ai_form_builder_import_status as _get_ai_form_builder_import_status,
	queue_ai_form_builder_import as _queue_ai_form_builder_import,
)
from ampower_form_builder.services.ai_form_autofill import (
	get_ai_form_autofill_status as _get_ai_form_autofill_status,
	queue_ai_form_autofill as _queue_ai_form_autofill,
)
from ampower_form_builder.services.doctype_creation import (
	create_doctype_from_template as _create_doctype_from_template,
)
from ampower_form_builder.services.template_versioning import (
	DEFAULT_FORM_VERSION_LABEL,
	backfill_template_version_metadata,
	build_versioned_form_name,
	normalize_form_version_label,
	suggest_next_version_label,
)


LAYOUT_FIELD_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML"}
TEMPLATE_DOCTYPE = "Dynamic Form Template"
SUBMISSION_DOCTYPE = "Dynamic Form Submission"
SKIPPED_IMPORT_FIELD_TYPES = {"HTML", "Fold", "Button", "Image", "Heading", "Geolocation", "Signature"}
SKIPPED_CHILD_TABLE_FIELD_TYPES = SKIPPED_IMPORT_FIELD_TYPES | {
    "Section Break",
    "Column Break",
    "Tab Break",
    "Table",
    "Table MultiSelect",
}
SCHEMA_FIELD_KEYS = {
    "fieldtype",
    "field_type",
    "fieldname",
    "field_name",
    "label",
    "field_label",
    "description",
    "placeholder",
    "default",
    "reqd",
    "read_only",
    "hidden",
    "depends_on",
    "options",
    "fetch_from",
    "formula",
    "precision",
    "table_row_title",
}
TEMPLATE_SCHEMA_CACHE_TTL = 60 * 10
ACTIVE_TEMPLATES_CACHE_TTL = 60 * 5
SQL_KEYWORDS = {
    "select", "insert", "update", "delete", "drop", "table", "from", "where", "join",
    "group", "order", "limit", "by", "and", "or", "into", "create", "alter", "index",
    "primary", "key", "constraint", "grant", "revoke", "union", "having", "distinct",
}


def _template_schema_cache_key(template_name):
    return f"ampower_form_builder:template_schema:{template_name}"


def _active_templates_cache_key(include_doctype_integration=False):
    suffix = ":with_integration" if include_doctype_integration else ":forms_only"
    return f"ampower_form_builder:active_templates{suffix}"


def invalidate_template_cache(*template_names):
    for template_name in template_names:
        template_name = (template_name or "").strip()
        if template_name:
            frappe.cache.delete_value(_template_schema_cache_key(template_name))


def invalidate_active_templates_cache():
    frappe.cache.delete_value(_active_templates_cache_key())
    frappe.cache.delete_value(_active_templates_cache_key(include_doctype_integration=True))


def _parse_schema_json(schema_json):
    if isinstance(schema_json, str):
        return json.loads(schema_json)
    if isinstance(schema_json, dict):
        return schema_json
    return {}


def _handle_api_exception(action, error):
    if isinstance(error, ValidationError):
        raise

    frappe.log_error(
        title=_("Ampower Form Builder API Error"),
        message=f"{action}\n\n{frappe.get_traceback()}",
    )
    frappe.throw(_("{0} failed. {1}").format(action, str(error)))


def _ensure_system_manager():
	if "System Manager" not in frappe.get_roles():
		raise frappe.PermissionError(_("Only System Managers can create DocTypes from templates."))


def _normalize_field(field):
    """Return a field dictionary with both legacy and current keys."""
    normalized = dict(field or {})

    field_type = normalized.get("fieldtype") or normalized.get("field_type")
    if field_type:
        normalized["fieldtype"] = field_type
        normalized["field_type"] = field_type

    fieldname = normalized.get("fieldname") or normalized.get("field_name")
    if fieldname:
        normalized["fieldname"] = fieldname
        normalized["field_name"] = fieldname

    label = normalized.get("label") or normalized.get("field_label")
    if label:
        normalized["label"] = label
        normalized["field_label"] = label

    if normalized.get("reqd") in (True, "1", 1):
        normalized["reqd"] = 1

    return normalized


def _sanitize_fieldname(value, fallback="field"):
    name = (value or "").strip().lower()
    name = re.sub(r"['\"]", "", name)
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        name = (fallback or "field").strip().lower()
        name = re.sub(r"['\"]", "", name)
        name = re.sub(r"[^a-z0-9]+", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
    if not name or not re.match(r"^[a-z]", name):
        name = f"field_{name}" if name else "field"
    if name in SQL_KEYWORDS:
        name = f"{name}_field"
    return name.rstrip("_") or "field"


def _sanitize_table_options(options):
    parsed = _parse_schema_json(options)
    columns = []
    rows = []
    for column in parsed.get("columns", []) if isinstance(parsed, dict) else []:
        column = dict(column or {})
        fieldname = _sanitize_fieldname(
            column.get("fieldname") or column.get("field_name") or column.get("label") or _("Column"),
            column.get("label") or column.get("fieldname") or _("Column"),
        )
        columns.append(
            {
                "label": column.get("label") or column.get("fieldname") or _("Column"),
                "fieldname": fieldname,
                "fieldtype": column.get("fieldtype") or "Data",
                "reqd": 1 if column.get("reqd") in (True, 1, "1") else 0,
                "placeholder": column.get("placeholder") or "",
                "fetch_from": column.get("fetch_from") or "",
                "formula": column.get("formula") or "",
                "precision": column.get("precision") or "",
                "options": column.get("options") or "",
            }
        )
    for row in parsed.get("rows", []) if isinstance(parsed, dict) else []:
        row = dict(row or {})
        rows.append(
            {
                "label": row.get("label") or _("Row"),
                "key": _sanitize_fieldname(row.get("key") or row.get("label") or _("Row"), row.get("label") or _("Row")),
            }
        )
    return {
        "mode": parsed.get("mode") or "table",
        "table_row_title": parsed.get("table_row_title") or parsed.get("row_title") or "",
        "image_column": parsed.get("image_column") or "",
        "columns": columns,
        "rows": rows,
    }


def _sanitize_schema_field(field):
    source = _normalize_field(field)
    sanitized = {key: source[key] for key in SCHEMA_FIELD_KEYS if key in source}
    sanitized["fieldname"] = _sanitize_fieldname(
        source.get("fieldname") or source.get("field_name") or source.get("label") or sanitized.get("fieldtype") or "field",
        source.get("label") or sanitized.get("fieldtype") or "field",
    )
    sanitized["field_name"] = sanitized["fieldname"]

    fieldtype = sanitized.get("fieldtype") or sanitized.get("field_type")
    if fieldtype in {"Link", "Dynamic Link"}:
        sanitized["options"] = source.get("options") or source.get("_doctype") or ""
    if fieldtype in {"Table", "Mixed Table"}:
        sanitized["options"] = json.dumps(_sanitize_table_options(source.get("options")))

    return sanitized


def _sanitize_section(section):
    section = dict(section or {})
    section_key = _sanitize_fieldname(
        section.get("section_key") or section.get("fieldname") or section.get("id") or section.get("label") or _("Section"),
        section.get("section_label") or section.get("label") or _("Section"),
    )
    return {
        "id": section.get("id"),
        "type": section.get("type") or "section",
        "item_type": section.get("item_type") or section.get("type") or "Section Break",
        "section_label": section.get("section_label") or section.get("label") or _("Untitled Section"),
        "section_key": section_key,
        "columns": [
            {
                "id": column.get("id"),
                "type": column.get("type") or "column",
                "section_id": column.get("section_id") or section.get("id"),
                "items": [_sanitize_schema_field(field) for field in column.get("items", [])],
            }
            for column in section.get("columns", [])
        ],
    }


def _sanitize_schema(schema):
    schema = _parse_schema_json(schema)

    sections = []
    if schema.get("sections"):
        sections = [_sanitize_section(section) for section in schema.get("sections", [])]

    fields = []
    if schema.get("fields"):
        sequence = 1
        for field in schema.get("fields", []):
            sanitized = _sanitize_schema_field(field)
            sanitized["sequence"] = sequence
            sequence += 1
            fields.append(sanitized)

    return {
        "version": schema.get("version") or 1,
        "form_name": schema.get("form_name") or "",
        "description": schema.get("description") or "",
        "fields": fields,
        "sections": sections,
    }


def _iter_schema_fields(schema):
    """Yield fields in visual order for both flat and nested schemas."""
    schema = _parse_schema_json(schema)

    if schema.get("fields"):
        for field in schema.get("fields", []):
            yield _normalize_field(field)
        return

    for section in schema.get("sections", []):
        section = dict(section or {})
        section_type = section.get("item_type") or section.get("type") or "Section Break"

        yield _normalize_field(
            {
                "fieldtype": section_type,
                "fieldname": section.get("section_key") or section.get("id"),
                "label": section.get("section_label") or section.get("label"),
                "section_key": section.get("section_key"),
                "section_label": section.get("section_label") or section.get("label"),
                "id": section.get("id"),
            }
        )

        for col_index, column in enumerate(section.get("columns", [])):
            if col_index > 0:
                yield _normalize_field(
                    {
                        "fieldtype": "Column Break",
                        "fieldname": f"column_break_{section.get('section_key') or section.get('id')}_{col_index + 1}",
                        "label": "Column Break",
                        "section_key": section.get("section_key"),
                    }
                )

            for field in column.get("items", []):
                yield _normalize_field(field)


def _extract_submission_columns(schema):
    return [
        {
            "fieldname": field.get("fieldname"),
            "label": field.get("label") or field.get("field_label"),
            "fieldtype": field.get("fieldtype") or field.get("field_type"),
        }
        for field in _iter_schema_fields(schema)
        if (field.get("fieldtype") or field.get("field_type")) not in LAYOUT_FIELD_TYPES
    ]


def _serialize_template_doc(doc):
    return {
        "name": doc.name,
        "form_name": doc.form_name,
        "display_name": doc.form_name,
        "form_type": getattr(doc, "form_type", "Form") or "Form",
        "target_doctype": getattr(doc, "target_doctype", "") or "",
        "base_form_name": getattr(doc, "base_form_name", "") or doc.form_name,
        "description": doc.description,
        "version_label": getattr(doc, "version_label", "") or DEFAULT_FORM_VERSION_LABEL,
        "version_group": getattr(doc, "version_group", "") or "",
        "source_template": getattr(doc, "source_template", "") or "",
        "is_latest_version": frappe.utils.cint(getattr(doc, "is_latest_version", 0)),
        "version": doc.version,
        "is_active": doc.is_active,
        "schema": _parse_schema_json(doc.schema_json),
    }


def _serialize_saved_template_doc(doc):
    return {
        "name": doc.name,
        "form_name": doc.form_name,
        "display_name": doc.form_name,
        "form_type": getattr(doc, "form_type", "Form") or "Form",
        "target_doctype": getattr(doc, "target_doctype", "") or "",
        "base_form_name": getattr(doc, "base_form_name", "") or doc.form_name,
        "description": doc.description,
        "is_active": doc.is_active,
        "version_label": getattr(doc, "version_label", "") or DEFAULT_FORM_VERSION_LABEL,
        "version_group": getattr(doc, "version_group", "") or "",
        "source_template": getattr(doc, "source_template", "") or "",
        "is_latest_version": frappe.utils.cint(getattr(doc, "is_latest_version", 0)),
        "version": doc.version,
    }


def _serialize_submission_doc(doc):
    return {
        "name": doc.name,
        "form_template": doc.form_template,
        "reference_doctype": getattr(doc, "reference_doctype", "") or "",
        "reference_name": getattr(doc, "reference_name", "") or "",
        "data": json.loads(doc.data_json) if doc.data_json else {},
        "status": doc.status,
        "submitted_on": str(doc.submitted_on) if doc.submitted_on else "",
        "owner": doc.owner,
    }


def _get_template_doc(template_name, permission="read"):
    doc = frappe.get_doc(TEMPLATE_DOCTYPE, template_name)
    doc.check_permission(permission)
    return doc


def _get_submission_doc(submission_name, permission="read"):
    doc = frappe.get_doc(SUBMISSION_DOCTYPE, submission_name)
    doc.check_permission(permission)
    return doc


def _normalize_json_payload(data):
    if isinstance(data, str):
        return json.loads(data)
    return data or {}


def _get_template_lookup_name(template_name=""):
    if template_name and frappe.db.exists(TEMPLATE_DOCTYPE, template_name):
        return template_name
    return None


def _build_template_doc(
    form_name,
    schema_json,
    description=None,
    template_name=None,
    is_active=1,
    form_type="Form",
    target_doctype="",
    base_form_name=None,
    version_label=None,
    version_group="",
    source_template="",
):
    serialized_schema = json.dumps(_sanitize_schema(schema_json), indent=2, sort_keys=True)
    is_active = frappe.utils.cint(is_active)
    form_type = (form_type or "Form").strip() or "Form"
    target_doctype = (target_doctype or "").strip()
    template_name = (template_name or "").strip()
    base_form_name = (base_form_name or "").strip() or form_name
    version_label = normalize_form_version_label(version_label or DEFAULT_FORM_VERSION_LABEL)
    version_group = (version_group or "").strip()
    source_template = (source_template or "").strip()

    existing_name = _get_template_lookup_name(template_name=template_name)
    if existing_name:
        doc = _get_template_doc(existing_name, permission="write")
        doc.form_name = form_name
        doc.schema_json = serialized_schema
        doc.form_type = form_type
        doc.target_doctype = target_doctype
        doc.base_form_name = base_form_name
        doc.version_label = version_label
        doc.version_group = version_group
        doc.source_template = source_template
        if description is not None:
            doc.description = description
        doc.is_active = is_active
        doc.save()

        if doc.name.strip() != form_name.strip():
            renamed_name = frappe.rename_doc(TEMPLATE_DOCTYPE, doc.name, form_name, force=True)
            doc = frappe.get_doc(TEMPLATE_DOCTYPE, renamed_name)
        return doc

    doc = frappe.get_doc({
        "doctype": TEMPLATE_DOCTYPE,
        "form_name": form_name,
        "schema_json": serialized_schema,
        "description": description or "",
        "is_active": is_active,
        "form_type": form_type,
        "target_doctype": target_doctype,
        "base_form_name": base_form_name,
        "version_label": version_label,
        "version_group": version_group,
        "source_template": source_template,
    })
    doc.insert()
    return doc


# ── Template APIs ──────────────────────────────────────────────────


@frappe.whitelist()
def get_form_schema(form_template):
    """Return the full schema JSON for a given form template.

    Args:
        form_template: Name (ID) of the Dynamic Form Template.

    Returns:
        dict with template metadata and parsed schema.
    """
    try:
        doc = _get_template_doc(form_template, permission="read")
        cache_key = _template_schema_cache_key(doc.name)
        cached = frappe.cache.get_value(cache_key)
        if cached:
            return cached

        payload = _serialize_template_doc(doc)
        frappe.cache.set_value(cache_key, payload, expires_in_sec=TEMPLATE_SCHEMA_CACHE_TTL)
        return payload
    except Exception as error:
        _handle_api_exception(_("Loading form schema"), error)


@frappe.whitelist()
def get_active_templates(include_doctype_integration=0):
    """Return a list of all active form templates (for dropdowns / selectors).

    Returns:
        list of dicts with name, form_name, description.
    """
    try:
        include_doctype_integration = bool(int(include_doctype_integration or 0))
        cached = frappe.cache.get_value(_active_templates_cache_key(include_doctype_integration))
        if cached:
            return cached

        filters = {"is_active": 1}
        if not include_doctype_integration:
            filters["form_type"] = "Form"

        payload = frappe.get_all(
            TEMPLATE_DOCTYPE,
            filters=filters,
            fields=[
                "name",
                "form_name",
                "form_type",
                "target_doctype",
                "description",
                "version",
                "base_form_name",
                "version_label",
                "version_group",
                "source_template",
                "is_latest_version",
            ],
            order_by="base_form_name asc, version_sort_key desc, modified desc",
        )
        for item in payload:
            item["display_name"] = item.get("form_name") or item.get("name")
            item["base_form_name"] = item.get("base_form_name") or item.get("form_name") or item.get("name")
            item["version_label"] = item.get("version_label") or DEFAULT_FORM_VERSION_LABEL
            item["is_latest_version"] = frappe.utils.cint(item.get("is_latest_version") or 0)
        frappe.cache.set_value(_active_templates_cache_key(include_doctype_integration), payload, expires_in_sec=ACTIVE_TEMPLATES_CACHE_TTL)
        return payload
    except Exception as error:
        _handle_api_exception(_("Loading active templates"), error)


@frappe.whitelist()
def get_template_version_context(template_name):
    """Return version-family metadata for creating a new template version."""
    try:
        doc = _get_template_doc(template_name, permission="write")
        backfill_template_version_metadata(doc)
        next_version_label = suggest_next_version_label(getattr(doc, "version_label", DEFAULT_FORM_VERSION_LABEL))
        base_form_name = getattr(doc, "base_form_name", "") or doc.form_name
        return {
            "template_name": doc.name,
            "form_name": doc.form_name,
            "base_form_name": base_form_name,
            "current_version_label": getattr(doc, "version_label", DEFAULT_FORM_VERSION_LABEL) or DEFAULT_FORM_VERSION_LABEL,
            "next_version_label": next_version_label,
            "suggested_form_name": build_versioned_form_name(base_form_name, next_version_label),
            "version_group": getattr(doc, "version_group", "") or "",
            "source_template": doc.name,
            "form_type": getattr(doc, "form_type", "Form") or "Form",
            "target_doctype": getattr(doc, "target_doctype", "") or "",
            "description": getattr(doc, "description", "") or "",
        }
    except Exception as error:
        _handle_api_exception(_("Loading form version details"), error)


@frappe.whitelist()
def enqueue_ai_form_builder_import(file_docname):
    """Queue an AI-assisted import for a previously uploaded file."""
    try:
        return _queue_ai_form_builder_import(file_docname=file_docname)
    except Exception as error:
        _handle_api_exception(_("Starting AI form import"), error)


@frappe.whitelist()
def get_ai_form_builder_import_status(job_id):
    """Fetch the current status for an AI-assisted import job."""
    try:
        return _get_ai_form_builder_import_status(job_id=job_id)
    except Exception as error:
        _handle_api_exception(_("Loading AI form import status"), error)


@frappe.whitelist()
def enqueue_ai_form_autofill(file_docname, template_name):
    """Queue an AI-assisted autofill job for a viewer template."""
    try:
        return _queue_ai_form_autofill(file_docname=file_docname, template_name=template_name)
    except Exception as error:
        _handle_api_exception(_("Starting AI form autofill"), error)


@frappe.whitelist()
def get_ai_form_autofill_status(job_id):
    """Fetch the current status for an AI-assisted autofill job."""
    try:
        return _get_ai_form_autofill_status(job_id=job_id)
    except Exception as error:
        _handle_api_exception(_("Loading AI form autofill status"), error)


def _serialize_docfield(df):
	return {
        "fieldname": df.fieldname,
        "label": df.label,
        "fieldtype": df.fieldtype,
        "options": df.options,
        "reqd": 1 if getattr(df, "reqd", 0) else 0,
        "read_only": 1 if getattr(df, "read_only", 0) else 0,
        "hidden": 1 if getattr(df, "hidden", 0) else 0,
        "description": getattr(df, "description", "") or "",
        "placeholder": getattr(df, "placeholder", "") or "",
        "default": getattr(df, "default", "") or "",
        "depends_on": getattr(df, "depends_on", "") or "",
        "precision": getattr(df, "precision", "") or "",
        "fetch_from": getattr(df, "fetch_from", "") or "",
    }


def _should_skip_import_field(df):
    if not getattr(df, "fieldname", None) and df.fieldtype not in {"Section Break", "Column Break", "Tab Break"}:
        return True
    return df.fieldtype in SKIPPED_IMPORT_FIELD_TYPES


def _should_skip_child_table_field(df):
    if not getattr(df, "fieldname", None):
        return True
    return df.fieldtype in SKIPPED_CHILD_TABLE_FIELD_TYPES


def _load_child_table_columns(child_doctype):
    try:
        child_meta = frappe.get_meta(child_doctype)
    except Exception:
        return []

    columns = []
    for child_df in child_meta.fields:
        if _should_skip_child_table_field(child_df):
            continue
        columns.append(_serialize_docfield(child_df))
    return columns


@frappe.whitelist()
def get_doctype_fields(doctype_name):
    """Return DocType metadata in a builder-friendly format.

    Includes child table columns so the builder can convert them into
    its own Table fields.
    """
    try:
        doctype_name = (doctype_name or "").strip()
        if not doctype_name:
            frappe.throw(_("DocType is required."))

        meta = frappe.get_meta(doctype_name)
        if not meta:
            frappe.throw(_("DocType {0} was not found.").format(frappe.bold(doctype_name)))

        fields = []
        child_tables = {}
        for df in meta.fields:
            if _should_skip_import_field(df):
                continue

            serialized = _serialize_docfield(df)
            fields.append(serialized)

            if df.fieldtype == "Table" and df.options:
                child_tables[df.fieldname] = {
                    "doctype": df.options,
                    "columns": _load_child_table_columns(df.options),
                }

        return {
            "doctype": doctype_name,
            "title": meta.name,
            "fields": fields,
            "child_tables": child_tables,
        }
    except Exception as error:
        _handle_api_exception(_("Loading DocType fields"), error)


@frappe.whitelist()
def save_form_template(
    form_name,
    schema_json,
    description=None,
    template_name=None,
    is_active=1,
    form_type="Form",
    target_doctype="",
    base_form_name=None,
    version_label=None,
    version_group="",
    source_template="",
):
    """Create or update a Dynamic Form Template.

    Updates happen only when an exact template document name is provided.
    New versions must therefore create a new document instead of silently
    overwriting an older form definition.

    Args:
        form_name: Human-readable name for the form.
        schema_json: JSON string of the form schema.
        description: Optional description text.
        template_name: Existing document name to update safely.
        is_active: Whether the template is active.
        form_type: "Form" or "Doctype Integration".
        target_doctype: Target DocType for Doctype Integration forms.
        base_form_name: Version family display name.
        version_label: Human-readable form version like 1.0 or 1.1.
        version_group: Internal version family identifier.
        source_template: Template that this version was copied from.

    Returns:
        dict with the saved template's name and version.
    """
    try:
        previous_template_name = (template_name or "").strip()
        form_name = (form_name or "").strip()
        if not form_name:
            version_label = normalize_form_version_label(version_label or DEFAULT_FORM_VERSION_LABEL)
            form_name = build_versioned_form_name(base_form_name, version_label)

        source_template = (source_template or "").strip()
        version_group = (version_group or "").strip()
        base_form_name = (base_form_name or "").strip()
        if source_template:
            source_doc = _get_template_doc(source_template, permission="read")
            version_group = version_group or getattr(source_doc, "version_group", "") or ""
            base_form_name = base_form_name or getattr(source_doc, "base_form_name", "") or source_doc.form_name

        doc = _build_template_doc(
            form_name=form_name,
            schema_json=schema_json,
            description=description,
            template_name=template_name,
            is_active=is_active,
            form_type=form_type,
            target_doctype=target_doctype,
            base_form_name=base_form_name or form_name,
            version_label=version_label or DEFAULT_FORM_VERSION_LABEL,
            version_group=version_group,
            source_template=source_template,
        )
        invalidate_template_cache(previous_template_name, doc.name, form_name)
        invalidate_active_templates_cache()
        frappe.db.commit()
        return _serialize_saved_template_doc(doc)
    except Exception as error:
        _handle_api_exception(_("Saving form template"), error)


@frappe.whitelist()
def create_doctype_from_template(template_name, doctype_name=None, module=None):
    """Create a custom DocType from a saved Dynamic Form Template."""
    try:
        _ensure_system_manager()
        template_name = (template_name or "").strip()
        if not template_name:
            frappe.throw(_("Template name is required."))

        template_doc = _get_template_doc(template_name, permission="read")
        return _create_doctype_from_template(template_doc, doctype_name=doctype_name, module=module)
    except Exception as error:
        _handle_api_exception(_("Creating DocType"), error)


# ── Submission APIs ────────────────────────────────────────────────


def _apply_reference_link(doc, reference_doctype=None, reference_name=None):
    reference_doctype = (reference_doctype or "").strip()
    reference_name = (reference_name or "").strip()

    if reference_doctype and reference_name:
        doc.reference_doctype = reference_doctype
        doc.reference_name = reference_name
        return

    doc.reference_doctype = ""
    doc.reference_name = ""


def _get_latest_submission_by_reference(form_template, reference_doctype, reference_name, permission="read"):
    form_template = (form_template or "").strip()
    reference_doctype = (reference_doctype or "").strip()
    reference_name = (reference_name or "").strip()

    if not form_template or not reference_doctype or not reference_name:
        return None

    result = frappe.db.sql(
        """
        SELECT name
        FROM `tabDynamic Form Submission`
        WHERE form_template = %s
          AND reference_doctype = %s
          AND reference_name = %s
        ORDER BY modified DESC
        LIMIT 1
        """,
        (form_template, reference_doctype, reference_name),
    )
    if not result:
        return None

    return _get_submission_doc(result[0][0], permission=permission)


@frappe.whitelist()
def save_submission(form_template, data, status="Submitted", reference_doctype=None, reference_name=None):
    """Create or update a Dynamic Form Submission record.

    Args:
        form_template: Name of the linked Dynamic Form Template.
        data: dict or JSON string of the form field values.
        status: Submission status (default: Submitted).
        reference_doctype: Optional parent DocType for the submission.
        reference_name: Optional parent document name for the submission.

    Returns:
        dict with the submission name and status.
    """
    try:
        payload = _normalize_json_payload(data)
        doc = _get_latest_submission_by_reference(form_template, reference_doctype, reference_name, permission="write")
        if doc:
            doc.data_json = json.dumps(payload)
            doc.status = status
            _apply_reference_link(doc, reference_doctype, reference_name)
            doc.save()
        else:
            doc = frappe.get_doc({
                "doctype": SUBMISSION_DOCTYPE,
                "form_template": form_template,
                "data_json": json.dumps(payload),
                "status": status,
            })
            _apply_reference_link(doc, reference_doctype, reference_name)
            doc.insert()
        frappe.db.commit()
        return {
            "name": doc.name,
            "status": doc.status,
            "submitted_on": str(doc.submitted_on),
        }
    except Exception as error:
        _handle_api_exception(_("Saving submission"), error)


@frappe.whitelist()
def update_submission(submission_name, data, status=None, reference_doctype=None, reference_name=None):
    """Update an existing Dynamic Form Submission record.

    Args:
        submission_name: Name of the existing submission.
        data: dict or JSON string of the form field values.
        status: Optional submission status override.
        reference_doctype: Optional parent DocType for the submission.
        reference_name: Optional parent document name for the submission.

    Returns:
        dict with the updated submission name and status.
    """
    try:
        payload = _normalize_json_payload(data)
        doc = _get_submission_doc(submission_name, permission="write")
        doc.data_json = json.dumps(payload)
        if status is not None:
            doc.status = status
        if reference_doctype is not None or reference_name is not None:
            _apply_reference_link(doc, reference_doctype, reference_name)
        doc.save()
        frappe.db.commit()
        return {
            "name": doc.name,
            "status": doc.status,
            "submitted_on": str(doc.submitted_on),
        }
    except Exception as error:
        _handle_api_exception(_("Updating submission"), error)


@frappe.whitelist()
def get_submissions(form_template, page=1, page_size=20, reference_doctype=None, reference_name=None):
    """List submissions for a given template with pagination.

    Returns the data in a table-friendly format with dynamic columns
    extracted from the template schema.

    Args:
        form_template: Name of the Dynamic Form Template.
        page: Page number (1-indexed).
        page_size: Number of records per page.
        reference_doctype: Optional parent DocType filter.
        reference_name: Optional parent document name filter.

    Returns:
        dict with columns, data rows, total count, and pagination info.
    """
    try:
        page = int(page)
        page_size = int(page_size)

        template = _get_template_doc(form_template, permission="read")
        schema = _parse_schema_json(template.schema_json)
        columns = _extract_submission_columns(schema)

        filters = {"form_template": form_template}
        reference_doctype = (reference_doctype or "").strip()
        reference_name = (reference_name or "").strip()
        if reference_doctype and reference_name:
            filters["reference_doctype"] = reference_doctype
            filters["reference_name"] = reference_name

        total = frappe.db.count(SUBMISSION_DOCTYPE, filters)

        submissions = frappe.get_all(
            SUBMISSION_DOCTYPE,
            filters=filters,
            fields=["name", "data_json", "status", "submitted_on", "owner"],
            order_by="submitted_on desc",
            start=(page - 1) * page_size,
            page_length=page_size,
        )

        rows = []
        for sub in submissions:
            data = json.loads(sub.data_json) if sub.data_json else {}
            row = {
                "_name": sub.name,
                "_status": sub.status,
                "_submitted_on": str(sub.submitted_on) if sub.submitted_on else "",
                "_owner": sub.owner,
            }
            row.update(data)
            rows.append(row)

        return {
            "columns": columns,
            "data": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as error:
        _handle_api_exception(_("Loading submissions"), error)


@frappe.whitelist()
def get_submission_by_reference(form_template, reference_doctype, reference_name):
    """Get the latest submission for a template and parent reference.

    Args:
        form_template: Name of the Dynamic Form Template.
        reference_doctype: Parent DocType for the submission.
        reference_name: Parent document name for the submission.

    Returns:
        dict with the submission metadata and parsed data, or None.
    """
    try:
        doc = _get_latest_submission_by_reference(form_template, reference_doctype, reference_name, permission="read")
        if not doc:
            return None
        return _serialize_submission_doc(doc)
    except Exception as error:
        _handle_api_exception(_("Loading submission"), error)


@frappe.whitelist()
def get_submission(submission_name):
    """Get a single submission with its full data.

    Args:
        submission_name: Name/ID of the Dynamic Form Submission.

    Returns:
        dict with submission metadata and parsed data.
    """
    try:
        doc = _get_submission_doc(submission_name, permission="read")
        return _serialize_submission_doc(doc)
    except Exception as error:
        _handle_api_exception(_("Loading submission"), error)
