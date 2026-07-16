"""Helpers for maintaining immutable, versioned form templates."""

from __future__ import annotations

import re

import frappe
from frappe import _

TEMPLATE_DOCTYPE = "Dynamic Form Template"
SUBMISSION_DOCTYPE = "Dynamic Form Submission"
DEFAULT_FORM_VERSION_LABEL = "1.0"
FORM_VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)*$")
VERSION_SORT_WIDTH = 6
VERSION_GROUP_PREFIX = "AFBG"
LOCKED_TEMPLATE_FIELDS = ("schema_json", "form_type", "target_doctype")


def normalize_form_version_label(value: str | None) -> str:
	"""Return a normalized dotted numeric version label."""
	label = str(value or DEFAULT_FORM_VERSION_LABEL).strip()
	if label.lower().startswith("v"):
		label = label[1:].strip()

	if not FORM_VERSION_PATTERN.fullmatch(label):
		frappe.throw(
			_("Form Version must use dotted numbers like 1, 1.1, or 2.0.3."),
			title=_("Validation Error"),
		)

	return ".".join(str(int(part)) for part in label.split("."))


def build_version_sort_key(version_label: str | None) -> str:
	"""Build a lexicographically sortable key from a dotted version label."""
	normalized_label = normalize_form_version_label(version_label)
	return ".".join(part.zfill(VERSION_SORT_WIDTH) for part in normalized_label.split("."))


def build_versioned_form_name(base_form_name: str | None, version_label: str | None) -> str:
	"""Return the default visible name for a new version."""
	base_name = str(base_form_name or "").strip()
	normalized_label = normalize_form_version_label(version_label)
	if not base_name:
		return f"v{normalized_label}"
	return f"{base_name} v{normalized_label}"


def suggest_next_version_label(current_version_label: str | None) -> str:
	"""Increment the trailing numeric segment of a dotted version label."""
	parts = [int(part) for part in normalize_form_version_label(current_version_label).split(".")]
	parts[-1] += 1
	return ".".join(str(part) for part in parts)


def ensure_template_version_metadata(template_doc) -> None:
	"""Populate and validate immutable version metadata on a template."""
	previous_doc = template_doc.get_doc_before_save() if hasattr(template_doc, "get_doc_before_save") else None

	template_doc.version_group = (
		str(getattr(template_doc, "version_group", "") or "").strip()
		or str(getattr(previous_doc, "version_group", "") or "").strip()
		or f"{VERSION_GROUP_PREFIX}-{frappe.generate_hash(length=10)}"
	)
	template_doc.base_form_name = (
		str(getattr(template_doc, "base_form_name", "") or "").strip()
		or str(getattr(previous_doc, "base_form_name", "") or "").strip()
		or str(getattr(template_doc, "form_name", "") or "").strip()
	)
	template_doc.version_label = normalize_form_version_label(
		getattr(template_doc, "version_label", None)
		or getattr(previous_doc, "version_label", None)
		or DEFAULT_FORM_VERSION_LABEL
	)
	template_doc.version_sort_key = build_version_sort_key(template_doc.version_label)
	template_doc.source_template = str(getattr(template_doc, "source_template", "") or "").strip()
	template_doc.is_latest_version = 1 if frappe.utils.cint(getattr(template_doc, "is_latest_version", 0)) else 0

	if not template_doc.base_form_name:
		frappe.throw(_("Base Form Name is required."), title=_("Validation Error"))

	if template_doc.source_template and not frappe.db.exists(TEMPLATE_DOCTYPE, template_doc.source_template):
		frappe.throw(
			_("Source Template {0} was not found.").format(frappe.bold(template_doc.source_template)),
			title=_("Validation Error"),
		)

	existing_name = frappe.db.get_value(
		TEMPLATE_DOCTYPE,
		{
			"version_group": template_doc.version_group,
			"version_label": template_doc.version_label,
			"name": ["!=", template_doc.name or ""],
		},
		"name",
	)
	if existing_name:
		frappe.throw(
			_(
				"Form version {0} already exists for {1}. Create a different version label."
			).format(
				frappe.bold(template_doc.version_label),
				frappe.bold(template_doc.base_form_name),
			),
			title=_("Validation Error"),
		)


def template_requires_version_backfill(template_doc) -> bool:
	"""Return True when a legacy template still lacks persisted version metadata."""
	return not all(
		[
			str(getattr(template_doc, "version_group", "") or "").strip(),
			str(getattr(template_doc, "base_form_name", "") or "").strip(),
			str(getattr(template_doc, "version_label", "") or "").strip(),
			str(getattr(template_doc, "version_sort_key", "") or "").strip(),
		]
	)


def backfill_template_version_metadata(template_doc) -> None:
	"""Persist version metadata for a legacy template only when first needed."""
	if not template_requires_version_backfill(template_doc):
		return

	ensure_template_version_metadata(template_doc)
	template_doc.flags.ignore_version = True
	template_doc.save()


def validate_template_mutability(template_doc) -> None:
	"""Block schema mutations once a form version already has submissions."""
	if template_doc.is_new():
		return

	if not any(template_doc.has_value_changed(fieldname) for fieldname in LOCKED_TEMPLATE_FIELDS):
		return

	if not frappe.db.exists(SUBMISSION_DOCTYPE, {"form_template": template_doc.name}):
		return

	frappe.throw(
		_(
			"This form version already has saved submissions. Create a new version in the builder instead of editing the existing schema."
		),
		title=_("Form Version Locked"),
	)


def sync_latest_version_flags(version_group: str | None, ignore_template_name: str | None = None) -> None:
	"""Keep a single latest-version marker inside each version group."""
	normalized_group = str(version_group or "").strip()
	if not normalized_group:
		return
	ignore_template_name = str(ignore_template_name or "").strip()

	versions = frappe.get_all(
		TEMPLATE_DOCTYPE,
		filters={
			"version_group": normalized_group,
			**({"name": ["!=", ignore_template_name]} if ignore_template_name else {}),
		},
		fields=["name"],
		order_by="version_sort_key desc, creation desc, modified desc",
	)

	latest_name = versions[0]["name"] if versions else ""
	for item in versions:
		frappe.db.set_value(
			TEMPLATE_DOCTYPE,
			item["name"],
			"is_latest_version",
			1 if item["name"] == latest_name else 0,
			update_modified=False,
		)
