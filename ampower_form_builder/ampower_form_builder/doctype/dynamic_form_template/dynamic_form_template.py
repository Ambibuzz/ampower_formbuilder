# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document

from ampower_form_builder.api import invalidate_active_templates_cache, invalidate_template_cache
from ampower_form_builder.services.doctype_integration import (
    FORM_TYPE_DOCTYPE_INTEGRATION,
    FORM_TYPE_FORM,
    cleanup_template_integration,
    sync_template_integration,
)
from ampower_form_builder.services.template_versioning import (
    ensure_template_version_metadata,
    sync_latest_version_flags,
    validate_template_mutability,
)


# Supported field types for validation
SUPPORTED_FIELD_TYPES = frozenset([
    "Data", "Date", "Datetime", "Time", "Attach", "Attach Image",
    "Link", "Dynamic Link", "Check", "Select", "Long Text", "Small Text",
    "Text Editor", "Color", "Number", "Radio", "Table", "Mixed Table",
    "Section Break", "Tab Break", "Column Break",
])

# Required keys every field definition must have
REQUIRED_FIELD_KEYS = ("fieldname", "label", "fieldtype")
SQL_KEYWORDS = {
    "select", "insert", "update", "delete", "drop", "table", "from", "where",
    "join", "group", "order", "limit", "by", "and", "or", "create", "alter",
}


class DynamicFormTemplate(Document):
    """Stores dynamic form definitions as JSON schema.

    The schema_json field holds a JSON object with a 'fields' array.
    Each field object describes one form control (type, label, options, etc.).
    """

    def validate(self):
        """Parse and validate the JSON schema on every save."""
        self._normalize_template_metadata()
        ensure_template_version_metadata(self)
        validate_template_mutability(self)
        self._validate_schema()
        self._auto_increment_version()

    def on_update(self):
        invalidate_template_cache(self.name)
        invalidate_active_templates_cache()
        sync_template_integration(self)
        sync_latest_version_flags(self.version_group)

    def on_trash(self):
        version_group = self.version_group
        invalidate_template_cache(self.name)
        invalidate_active_templates_cache()
        cleanup_template_integration(self)
        sync_latest_version_flags(version_group, ignore_template_name=self.name)

    def _normalize_template_metadata(self):
        """Keep the builder metadata coherent across form types."""
        self.form_type = (self.form_type or FORM_TYPE_FORM).strip() or FORM_TYPE_FORM
        self.target_doctype = (self.target_doctype or "").strip()

        if self.form_type == FORM_TYPE_DOCTYPE_INTEGRATION and not self.target_doctype:
            frappe.throw(
                frappe._("Target DocType is required when Form Type is Doctype Integration."),
                title=frappe._("Validation Error"),
            )

        if self.target_doctype:
            if not frappe.db.exists("DocType", self.target_doctype):
                frappe.throw(
                    frappe._("Target DocType {0} was not found.").format(frappe.bold(self.target_doctype)),
                    title=frappe._("Validation Error"),
                )

            target_meta = frappe.get_meta(self.target_doctype)
            if getattr(target_meta, "istable", False):
                frappe.throw(
                    frappe._("Target DocType {0} cannot be a child table.").format(frappe.bold(self.target_doctype)),
                    title=frappe._("Validation Error"),
                )

    # ── Schema validation ──────────────────────────────────────────

    def _validate_schema(self):
        """Ensure schema_json is valid and contains well-formed field defs."""
        schema = self._parse_schema_json()
        fields = self._extract_fields(schema)
        seen_fieldnames = set()

        for idx, field_def in enumerate(fields):
            self._validate_field_definition(field_def, idx, seen_fieldnames)

    def _parse_schema_json(self):
        """Deserialize schema_json; raise on invalid JSON."""
        try:
            schema = json.loads(self.schema_json)
        except (json.JSONDecodeError, TypeError) as exc:
            frappe.throw(
                frappe._("Invalid JSON in Schema: {0}").format(str(exc)),
                title=frappe._("Schema Error"),
            )
        if not isinstance(schema, dict):
            frappe.throw(
                frappe._("Schema must be a JSON object with a 'fields' key."),
                title=frappe._("Schema Error"),
            )
        return schema

    @staticmethod
    def _extract_fields(schema):
        """Return the 'fields' list from the schema dict."""
        fields = schema.get("fields")
        if not isinstance(fields, list) or not fields:
            frappe.throw(
                frappe._("Schema must contain a non-empty 'fields' array."),
                title=frappe._("Schema Error"),
            )
        return fields

    @staticmethod
    def _validate_field_definition(field_def, index, seen_fieldnames):
        """Validate a single field definition object."""
        if not isinstance(field_def, dict):
            frappe.throw(
                frappe._("Field at index {0} must be a JSON object.").format(index),
                title=frappe._("Schema Error"),
            )

        # Check required keys
        for key in REQUIRED_FIELD_KEYS:
            if not field_def.get(key):
                frappe.throw(
                    frappe._("Field at index {0} is missing required key '{1}'.").format(index, key),
                    title=frappe._("Schema Error"),
                )

        # Validate field type
        fieldtype = field_def["fieldtype"]
        field_def["fieldtype"] = fieldtype
        if fieldtype not in SUPPORTED_FIELD_TYPES:
            frappe.throw(
                frappe._("Field '{0}' has unsupported type '{1}'.").format(
                    field_def.get("label", index), fieldtype
                ),
                title=frappe._("Schema Error"),
            )

        # Unique fieldnames
        fieldname = field_def["fieldname"]
        if fieldtype not in {"Section Break", "Tab Break", "Column Break"}:
            if not fieldname:
                frappe.throw(
                    frappe._("Fieldname cannot be empty."),
                    title=frappe._("Schema Error"),
                )
            if (
                not fieldname[0].isalpha()
                or not all(char.islower() or char.isdigit() or char == "_" for char in fieldname)
                or fieldname in SQL_KEYWORDS
            ):
                frappe.throw(
                    frappe._("Fieldname '{0}' is invalid. Use lowercase letters, numbers, underscores, and avoid SQL keywords.").format(fieldname),
                    title=frappe._("Schema Error"),
                )
            if fieldname in seen_fieldnames:
                frappe.throw(
                    frappe._("Duplicate fieldname '{0}' at index {1}.").format(fieldname, index),
                    title=frappe._("Schema Error"),
                )
            seen_fieldnames.add(fieldname)

        # Select fields need configuration payloads. Table fields can be
        # rendered from either the legacy options JSON or the nested schema.
        if fieldtype in {"Select", "Radio"} and not field_def.get("options"):
            frappe.throw(
                frappe._("{0} field '{1}' must have 'options'.").format(fieldtype, field_def["label"]),
                title=frappe._("Schema Error"),
            )
        if field_def.get("reqd") and field_def.get("hidden"):
            frappe.throw(
                frappe._("Field '{0}' cannot be both required and hidden.").format(field_def["label"]),
                title=frappe._("Schema Error"),
            )
        if fieldtype == "Link" and not field_def.get("options"):
            frappe.throw(
                frappe._("Field '{0}' must define Options / DocType.").format(field_def["label"]),
                title=frappe._("Schema Error"),
            )
        if fieldtype == "Dynamic Link" and not field_def.get("options"):
            frappe.throw(
                frappe._("Field '{0}' must define Options / Source Field.").format(field_def["label"]),
                title=frappe._("Schema Error"),
            )
        if fieldtype in {"Table", "Mixed Table"}:
            try:
                table_config = json.loads(field_def.get("options") or "{}")
            except Exception:
                table_config = {}
            if not (
                field_def.get("table_columns")
                or field_def.get("columns")
                or table_config.get("columns")
            ):
                frappe.throw(
                    frappe._("Table field '{0}' must define columns.").format(field_def["label"]),
                    title=frappe._("Schema Error"),
                )
            if fieldtype == "Mixed Table" and not (
                field_def.get("table_rows")
                or field_def.get("rows")
                or table_config.get("rows")
            ):
                frappe.throw(
                    frappe._("Mixed Table field '{0}' must define rows.").format(field_def["label"]),
                    title=frappe._("Schema Error"),
                )

    # ── Version management ─────────────────────────────────────────

    def _auto_increment_version(self):
        """Bump version when the schema changes on an existing document."""
        if not self.is_new() and self.has_value_changed("schema_json"):
            self.version = (self.version or 0) + 1
