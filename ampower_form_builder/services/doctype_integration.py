"""Integration helpers for embedding a dynamic form inside a target DocType."""

from __future__ import annotations

import json

import frappe
from frappe import _

TEMPLATE_DOCTYPE = "Dynamic Form Template"
SUBMISSION_DOCTYPE = "Dynamic Form Submission"

FORM_TYPE_FORM = "Form"
FORM_TYPE_DOCTYPE_INTEGRATION = "Doctype Integration"

LEGACY_INTEGRATION_SECTION_FIELDNAME = "afb_integration_section"
INTEGRATION_TAB_FIELDNAME = "afb_integration_tab"
INTEGRATION_FORM_FIELDNAME = "afb_integration_form"
INTEGRATION_VIEW_FIELDNAME = "afb_integration_view"
INTEGRATION_SUBMISSION_FIELDNAME = "afb_integration_submission"
INTEGRATION_VIEW_ROOT_CLASS = "afb-integration-root"
INTEGRATION_CLIENT_SCRIPT_NAME_PREFIX = "Ampower Form Builder Integration - "
INTEGRATION_TAB_LABEL = _("Ampower Form Integration")
INTEGRATION_PLACEHOLDER = _("Select a form to render the live viewer.")
INTEGRATION_LINK_FILTERS = json.dumps(
    [
        [TEMPLATE_DOCTYPE, "form_type", "=", FORM_TYPE_DOCTYPE_INTEGRATION],
        [TEMPLATE_DOCTYPE, "target_doctype", "=", "eval:doc.doctype"],
        [TEMPLATE_DOCTYPE, "is_active", "=", 1],
    ]
)


class DoctypeIntegrationManager:
    """Synchronize the shared integration UI for a target DocType.

    The target DocType gets a single reusable integration tab containing:
    - a form selector
    - an HTML host for the embedded viewer
    - a submission reference link

    The tab is shared by all integration templates targeting that DocType.
    """

    def __init__(self, template_doc):
        self.template_doc = template_doc

    @classmethod
    def from_template(cls, template_doc):
        return cls(template_doc)

    def sync(self, previous_target_doctype=None, previous_form_type=None):
        """Create or remove integration artifacts based on the current state."""
        targets = self._candidate_targets(previous_target_doctype, previous_form_type)

        for target_doctype in targets:
            if self._has_integration_templates(target_doctype):
                self._ensure_target_doctype(target_doctype)
            else:
                self._remove_target_doctype(target_doctype)

    def cleanup(self):
        """Remove the integration artifacts if no integration templates remain."""
        target_doctype = self._current_target_doctype()
        if not target_doctype:
            return

        if self._has_integration_templates(target_doctype):
            return

        self._remove_target_doctype(target_doctype)

    def _current_target_doctype(self):
        return (getattr(self.template_doc, "target_doctype", "") or "").strip()

    def _candidate_targets(self, previous_target_doctype=None, previous_form_type=None):
        targets = {
            (previous_target_doctype or "").strip(),
            self._current_target_doctype(),
        }
        return [target for target in targets if target]

    def _has_integration_templates(self, target_doctype):
        return bool(
            frappe.db.exists(
                TEMPLATE_DOCTYPE,
                {
                    "form_type": FORM_TYPE_DOCTYPE_INTEGRATION,
                    "target_doctype": target_doctype,
                    "is_active": 1,
                },
            )
        )

    def _ensure_target_doctype(self, target_doctype):
        self._remove_legacy_container(target_doctype)
        self._upsert_custom_fields(target_doctype)
        self._upsert_client_script(target_doctype)
        frappe.clear_cache(doctype=target_doctype)
        frappe.db.updatedb(target_doctype)

    def _remove_target_doctype(self, target_doctype):
        removed = self._remove_custom_field(target_doctype, INTEGRATION_TAB_FIELDNAME)
        removed = self._remove_custom_field(target_doctype, LEGACY_INTEGRATION_SECTION_FIELDNAME) or removed
        for fieldname in (
            INTEGRATION_FORM_FIELDNAME,
            INTEGRATION_VIEW_FIELDNAME,
            INTEGRATION_SUBMISSION_FIELDNAME,
        ):
            removed = self._remove_custom_field(target_doctype, fieldname) or removed

        script_name = self._client_script_name(target_doctype)
        if frappe.db.exists("Client Script", script_name):
            frappe.delete_doc(
                "Client Script",
                script_name,
                force=True,
                ignore_permissions=True,
            )

        if removed:
            frappe.clear_cache(doctype=target_doctype)
            frappe.db.updatedb(target_doctype)

    def _remove_legacy_container(self, target_doctype):
        self._remove_custom_field(target_doctype, LEGACY_INTEGRATION_SECTION_FIELDNAME)

    def _remove_custom_field(self, target_doctype, fieldname):
        custom_field_name = f"{target_doctype}-{fieldname}"
        if not frappe.db.exists("Custom Field", custom_field_name):
            return False

        frappe.delete_doc(
            "Custom Field",
            custom_field_name,
            force=True,
            ignore_permissions=True,
        )
        return True

    def _upsert_custom_fields(self, target_doctype):
        for field_config in self._build_custom_fields():
            self._upsert_custom_field(target_doctype, field_config)

    def _upsert_custom_field(self, target_doctype, field_config):
        fieldname = field_config["fieldname"]
        custom_field_name = f"{target_doctype}-{fieldname}"

        if frappe.db.exists("Custom Field", custom_field_name):
            doc = frappe.get_doc("Custom Field", custom_field_name)
        else:
            doc = frappe.get_doc(
                {
                    "doctype": "Custom Field",
                    "dt": target_doctype,
                    **field_config,
                }
            )

        doc.dt = target_doctype
        for key, value in field_config.items():
            setattr(doc, key, value)

        doc.flags.ignore_permissions = True
        if doc.is_new():
            doc.insert(ignore_permissions=True)
            return

        doc.save(ignore_permissions=True)

    def _build_custom_fields(self):
        return [
            {
                "fieldname": INTEGRATION_TAB_FIELDNAME,
                "fieldtype": "Tab Break",
                "label": INTEGRATION_TAB_LABEL,
                "insert_after": "append",
            },
            {
                "fieldname": INTEGRATION_FORM_FIELDNAME,
                "fieldtype": "Link",
                "label": _("Select Form"),
                "options": TEMPLATE_DOCTYPE,
                "insert_after": INTEGRATION_TAB_FIELDNAME,
                "link_filters": INTEGRATION_LINK_FILTERS,
                "description": _(""),
            },
            {
                "fieldname": INTEGRATION_VIEW_FIELDNAME,
                "fieldtype": "HTML",
                "label": _("Form View"),
                "insert_after": INTEGRATION_FORM_FIELDNAME,
                "options": (
                    f'<div class="{INTEGRATION_VIEW_ROOT_CLASS}">'
                    f'<div class="text-muted small">{frappe.utils.escape_html(INTEGRATION_PLACEHOLDER)}</div>'
                    "</div>"
                ),
            },
            {
                "fieldname": INTEGRATION_SUBMISSION_FIELDNAME,
                "fieldtype": "Link",
                "label": _("Submission Reference"),
                "options": SUBMISSION_DOCTYPE,
                "insert_after": INTEGRATION_VIEW_FIELDNAME,
                "read_only": 1,
                "no_copy": 1,
                "description": _(""),
            },
        ]

    def _client_script_name(self, target_doctype):
        return f"{INTEGRATION_CLIENT_SCRIPT_NAME_PREFIX}{target_doctype}"

    def _upsert_client_script(self, target_doctype):
        script_name = self._client_script_name(target_doctype)
        script = self._build_client_script(target_doctype)

        if frappe.db.exists("Client Script", script_name):
            doc = frappe.get_doc("Client Script", script_name)
            doc.script = script
            doc.enabled = 1
            doc.view = "Form"
            doc.module = "Ampower Form Builder"
            doc.flags.ignore_permissions = True
            doc.save()
            return

        doc = frappe.get_doc(
            {
                "doctype": "Client Script",
                "name": script_name,
                "dt": target_doctype,
                "view": "Form",
                "enabled": 1,
                "module": "Ampower Form Builder",
                "script": script,
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()

    def _build_client_script(self, target_doctype):
        form_field = INTEGRATION_FORM_FIELDNAME
        view_field = INTEGRATION_VIEW_FIELDNAME
        submission_field = INTEGRATION_SUBMISSION_FIELDNAME
        root_class = INTEGRATION_VIEW_ROOT_CLASS

        return f"""
function afbDestroyIntegrationViewer(frm) {{
	if (frm._afbIntegrationViewer?.destroy) {{
		frm._afbIntegrationViewer.destroy();
	}}
	frm._afbIntegrationViewer = null;
	frm._afbIntegrationRenderSignature = "";
	frm._afbIntegrationTemplateName = "";
}}

function afbGetIntegrationViewer(frm) {{
	return frm._afbIntegrationViewer || null;
}}

function afbToggleIntegrationFields(frm, show) {{
	const visible = Boolean(show);
	if (frm._afbIntegrationFieldsVisible === visible) {{
		return;
	}}

	frm._afbIntegrationFieldsVisible = visible;

	[
		"{INTEGRATION_TAB_FIELDNAME}",
		"{form_field}",
		"{view_field}",
		"{submission_field}",
	].forEach((fieldname) => {{
		frm.toggle_display(fieldname, visible);
		frm.refresh_field(fieldname);
	}});
}}

function afbCanShowIntegrationFields(frm) {{
	return Boolean(frm?.doc?.name) && !frm.is_new();
}}

function afbCanAutofillSubform(frm) {{
	return afbCanShowIntegrationFields(frm) && Boolean(frm.doc["{form_field}"]);
}}

function afbEnsureIntegrationMountPoint(viewField) {{
	let mountPoint = viewField.$wrapper.find(".{root_class}").get(0);
	if (!mountPoint) {{
		viewField.html(`<div class="{root_class}"></div>`);
		mountPoint = viewField.$wrapper.find(".{root_class}").get(0);
	}}
	return mountPoint;
}}

function afbRenderIntegrationViewer(frm) {{
	const viewField = frm.fields_dict["{view_field}"];
	if (!viewField) return;

	const canShowIntegrationFields = afbCanShowIntegrationFields(frm);
	afbToggleIntegrationFields(frm, canShowIntegrationFields);
	if (!canShowIntegrationFields) {{
		afbDestroyIntegrationViewer(frm);
		viewField.html("");
		frm.refresh_field("{view_field}");
		return;
	}}

	const nextProps = {{
		page: frm.page,
		frm: frm,
		templateName: frm.doc["{form_field}"] || "",
		embedded: true,
		parentDoctype: frm.doctype,
		parentDocname: frm.doc.name || "",
		submissionName: frm.doc["{submission_field}"] || "",
		submissionFieldname: "{submission_field}",
		autofillSubmissionStatus: "Draft",
		onSubmissionSaved: async (submissionName) => {{
			if (submissionName && frm.doc["{submission_field}"] !== submissionName) {{
				await frm.set_value("{submission_field}", submissionName);
				frm.refresh_field("{submission_field}");
			}}
			if (frm.is_dirty()) {{
				frm._afbSkipSubmissionSync = true;
				try {{
					await frm.save();
				}} finally {{
					frm._afbSkipSubmissionSync = false;
				}}
			}}
			if (frm._afbReloadAfterSubmissionSave && typeof frm.reload_doc === "function") {{
				await frm.reload_doc();
			}}
		}},
	}};
	const nextSignature = JSON.stringify({{
		templateName: nextProps.templateName,
		parentDocname: nextProps.parentDocname,
		submissionName: nextProps.submissionName,
		docstatus: frm.doc.docstatus || 0,
	}});

	let mountPoint = afbEnsureIntegrationMountPoint(viewField);
	if (!mountPoint || !window.frappe?.ui?.AmpowerFormViewer) return;

	if (
		frm._afbIntegrationViewer
		&& frm._afbIntegrationViewer.wrapper === mountPoint
	) {{
		if (frm._afbIntegrationTemplateName !== nextProps.templateName) {{
			afbDestroyIntegrationViewer(frm);
			mountPoint = afbEnsureIntegrationMountPoint(viewField);
			if (!mountPoint) return;
		}} else if (frm._afbIntegrationRenderSignature !== nextSignature) {{
			frm._afbIntegrationViewer.update(nextProps);
			frm._afbIntegrationRenderSignature = nextSignature;
		}}
		if (frm._afbIntegrationViewer) {{
			return;
		}}
	}}

	afbDestroyIntegrationViewer(frm);
	frm._afbIntegrationViewer = new frappe.ui.AmpowerFormViewer({{
		wrapper: mountPoint,
		...nextProps,
	}});
	frm._afbIntegrationRenderSignature = nextSignature;
	frm._afbIntegrationTemplateName = nextProps.templateName;
}}

async function afbOpenAutofillSubform(frm) {{
	const viewer = afbGetIntegrationViewer(frm);
	if (!viewer?.vm?.openAutofillModal) {{
		afbRenderIntegrationViewer(frm);
	}}

	const mountedViewer = afbGetIntegrationViewer(frm);
	if (!mountedViewer?.vm?.openAutofillModal) {{
		frappe.msgprint({{
			title: __("Autofill Unavailable"),
			message: __("Load and save a form template before using subform autofill."),
			indicator: "orange",
		}});
		return;
	}}

	mountedViewer.vm.openAutofillModal();
}}

frappe.ui.form.on({json.dumps(target_doctype)}, {{
	onload_post_render(frm) {{
		afbRenderIntegrationViewer(frm);
	}},
	refresh(frm) {{
		afbRenderIntegrationViewer(frm);
		if (afbCanAutofillSubform(frm)) {{
			frm.add_custom_button(__("Autofill Subform"), () => afbOpenAutofillSubform(frm));
		}}
	}},
	async "{form_field}"(frm) {{
		if (frm.doc["{submission_field}"]) {{
			await frm.set_value("{submission_field}", "");
			frm.refresh_field("{submission_field}");
		}}
		afbDestroyIntegrationViewer(frm);
		afbRenderIntegrationViewer(frm);
	}},
}});
"""


def sync_template_integration(template_doc):
    """Public helper used by the Dynamic Form Template controller."""
    previous_target_doctype = ""
    previous_form_type = ""

    previous_doc = template_doc.get_doc_before_save() if hasattr(template_doc, "get_doc_before_save") else None
    if previous_doc:
        previous_target_doctype = getattr(previous_doc, "target_doctype", "") or ""
        previous_form_type = getattr(previous_doc, "form_type", "") or ""

    DoctypeIntegrationManager.from_template(template_doc).sync(
        previous_target_doctype=previous_target_doctype,
        previous_form_type=previous_form_type,
    )


def cleanup_template_integration(template_doc):
    """Remove integration artifacts when the template is deleted."""
    DoctypeIntegrationManager.from_template(template_doc).cleanup()


def rebuild_all_integration_client_scripts():
    """Rebuild all active Doctype Integration custom fields and client scripts."""
    template_names = frappe.get_all(
        TEMPLATE_DOCTYPE,
        filters={
            "is_active": 1,
            "form_type": FORM_TYPE_DOCTYPE_INTEGRATION,
        },
        pluck="name",
    )

    for template_name in template_names:
        template_doc = frappe.get_doc(TEMPLATE_DOCTYPE, template_name)
        target_doctype = (getattr(template_doc, "target_doctype", "") or "").strip()
        if not target_doctype:
            continue
        DoctypeIntegrationManager.from_template(template_doc)._ensure_target_doctype(target_doctype)
