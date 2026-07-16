frappe.pages["form-builder-docs"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Form Builder Docs",
		single_column: true,
	});

	wrapper.classList.add("form-builder-docs-page");

	const escapeHtml = (value) =>
		String(value ?? "")
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;");

	const list = (items, ordered = false) => {
		const tag = ordered ? "ol" : "ul";
		return `<${tag} class="afb-docs-list">${items.map((item) => `<li>${item}</li>`).join("")}</${tag}>`;
	};

	const orderedList = (items) => list(items, true);

	const table = (headers, rows) => `
		<div class="afb-docs-table-wrap">
			<table class="afb-docs-table">
				<thead>
					<tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr>
				</thead>
				<tbody>
					${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}
				</tbody>
			</table>
		</div>
	`;

	const codeBlock = (code, language = "") => `
		<pre class="afb-docs-code${language ? ` is-${language}` : ""}"><code>${escapeHtml(code)}</code></pre>
	`;

	const callout = (title, content, tone = "info") => `
		<div class="afb-docs-callout is-${tone}">
			<h4>${title}</h4>
			<div class="afb-docs-callout-body">${content}</div>
		</div>
	`;

	const card = (title, content, tone = "") => `
		<article class="afb-docs-card${tone ? ` is-${tone}` : ""}">
			<h3>${title}</h3>
			<div class="afb-docs-card-body">${content}</div>
		</article>
	`;

	const sections = {
		overview: {
			nav: "Start here",
			navSummary: "Builder, viewer, and AI",
			eyebrow: "Overview",
			title: "How the app fits together",
			summary: "A quick map of the builder, viewer, DocType creation and integration, and AI features before you start configuring anything.",
			content: `
				<p class="afb-docs-lead">
					AmPower Form Builder stores form definitions as JSON, renders them dynamically, and keeps the data model intentionally small.
					Use this guide if you want to install the app, import an existing DocType, create a real DocType from a saved form, embed a form into another DocType, or let AI draft and autofill forms for you.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Recommended flow", list([
						"Rebuild assets when needed.",
						"Fill <strong>Form Builder Config</strong> with OpenAI and Google Vision credentials.",
						"Import a DocType or create a new form from scratch.",
						"Use <strong>Create DocType</strong> when the builder form should become a real Frappe DocType.",
						"Use <strong>Doctype Integration</strong> when the form should appear inside another DocType.",
						"Use <strong>Print Builder</strong> when the saved template needs a PDF layout with repeatable header and footer sections.",
						"Use AI draft and AI autofill only as a reviewable starting point.",
					]))}
					${card("What gets stored", list([
						"<strong>Dynamic Form Template</strong> stores the schema, metadata, form type, and target DocType.",
						"<strong>Dynamic Form Submission</strong> stores the submitted JSON payload.",
						"<strong>Form Builder Config</strong> stores the app-wide AI and report configuration.",
						"Most forms stay template-backed, but System Managers can materialize a saved form into a real DocType when needed.",
					]))}
				</div>
				${callout("Good default behavior", `
					<p>
						The builder supports standalone forms and integration forms, and the viewer can autofill a saved template from a PDF or image.
						When the source code changes, rebuild assets so Desk loads the latest bundle.
					</p>
				`, "brand")}
				<div class="afb-docs-grid three-up">
					${card("Builder route", `<p><code>/app/form-builder</code></p>`)}
					${card("Viewer route", `<p><code>/app/form-viewer?template=&lt;template-name&gt;</code></p>`)}
					${card("Print route", `<p><code>/app/print-builder</code></p>`)}
					${card("Docs route", `<p><code>/app/form-builder-docs</code></p>`)}
				</div>
				`,
			},
		permissions: {
			nav: "Permissions",
			navSummary: "Roles and access",
			eyebrow: "Access control",
			title: "Form Builder roles and permissions",
			summary: "Two app roles cover setup and daily use: one for full admin control and one for template and submission work.",
			content: `
				<p class="afb-docs-lead">
					Use the app roles instead of relying on generic system access for day-to-day work.
					The shipped fixtures include the roles below so teams can assign them consistently across sites.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Form Builder Admin", list([
						"Full access to all AmPower Form Builder doctypes.",
						"Can create, read, write, delete, submit, cancel, amend, export, import, print, report, select, and share.",
						"Use for setup, maintenance, and AI configuration.",
					]))}
					${card("Form Builder User", list([
						"Template permissions: read, select, import.",
						"Submission permissions: create, read, write, submit.",
						"Use for daily template use and data capture.",
					]))}
				</div>
				${callout("Page access", `
					<p>
						The builder, viewer, and docs pages are assigned to both roles so users can open the tools they need.
						The DocType permissions still decide what they can actually save or submit.
					</p>
				`, "brand")}
				${card("Access rule of thumb", list([
					"If someone needs to configure the app, give them <strong>Form Builder Admin</strong>.",
					"If someone only needs to work with templates and submissions, give them <strong>Form Builder User</strong>.",
				]))}
			`,
		},
		config: {
			nav: "Config",
			navSummary: "Global AI and reports",
			eyebrow: "System setup",
			title: "Configure Form Builder Config",
			summary: "This single record controls AI import, AI autofill, and report defaults. Fill it carefully because it affects every user.",
			content: `
				<p class="afb-docs-lead">
					The <strong>Form Builder Config</strong> DocType is the central setup record.
					The service layer reads it directly, trims whitespace, and validates that the required AI fields are present before the AI flows can start.
				</p>
				${table(
					["Field", "Required", "Purpose"],
					[
						["<strong>OpenAI API Key</strong>", "Yes", "Used for both AI draft generation and AI autofill requests."],
						["<strong>OpenAI API URL</strong>", "Recommended", "Defaults to <code>https://api.openai.com/v1/chat/completions</code>."],
						["<strong>Google Service Account JSON</strong>", "Yes", "Used for Google Vision OCR before the model sees the content."],
						["<strong>Form Builder System Prompt</strong>", "Optional", "Custom prompt for AI form drafting."],
						["<strong>Autofill System Prompt</strong>", "Optional", "Custom prompt for AI autofill mapping."],
					]
				)}
				<div class="afb-docs-grid two-up">
					${card("Google service account JSON", `
						<p>Paste the full JSON object from Google Cloud, not just a key pair snippet.</p>
						${codeBlock(`{
  "client_email": "vision-ocr@project.iam.gserviceaccount.com",
  "private_key": "-----BEGIN PRIVATE KEY-----..."
}`, "json")}
						<p class="afb-docs-note">The code expects at least <code>client_email</code> and <code>private_key</code>. The optional <code>token_uri</code> is respected when present.</p>
					`)}
					${card("Why prompts matter", list([
						"The default prompt is conservative and prefers valid structure over guesswork.",
						"Use a custom prompt only when your forms follow a stable pattern or a strict house style.",
						"Keep the prompt short and task-specific so the model stays focused on structure and field names.",
					]))}
				</div>
				${callout("Tip", `
					<p>
						If AI import or autofill fails with a configuration error, first check the <strong>Form Builder Config</strong> record.
						The backend throws a clear message for missing OpenAI key, missing API URL, missing Google JSON, or invalid JSON payloads.
					</p>
				`, "warning")}
			`,
		},
		import_doctype: {
			nav: "Import DocType",
			navSummary: "Load a source DocType",
			eyebrow: "Starting point",
			title: "Import a DocType and turn it into a form",
			summary: "Use the builder menu to load an existing DocType as a starting point, then reshape it into a cleaner form template.",
			content: `
				<p class="afb-docs-lead">
					If you already have a DocType, the fastest way to start is to load it into the builder.
					The app converts the DocType fields into builder sections, columns, and fields, so you can refine the layout instead of recreating everything manually.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Builder menu action", list([
						"Open <strong>/app/form-builder</strong>.",
						"Choose <strong>Load Doctype Form</strong> from the menu.",
						"Select the source DocType.",
						"Review the imported canvas and save it as a new template or continue editing the imported draft.",
					]))}
					${card("What is imported", list([
						"Tab Breaks and Section Breaks are preserved as builder sections.",
						"Column Breaks are preserved as builder columns.",
						"Child table fields are converted into builder <strong>Table</strong> fields with table columns.",
						"Field labels, fieldnames, defaults, descriptions, options, and basic flags are carried forward where possible.",
					]))}
				</div>
				${callout("What the importer skips", `
					<p>
						Some field types are intentionally skipped because they do not translate cleanly into the builder canvas.
						That is expected behavior, not a bug.
					</p>
					${list([
						"<strong>Skipped on import:</strong> HTML, Fold, Button, Image, Heading, Geolocation, Signature.",
						"<strong>Skipped in child tables:</strong> layout-only fields and unsupported fields that cannot be rebuilt as table columns.",
						"Unsupported field types are normalized to safe builder equivalents where possible, often falling back to <strong>Data</strong>.",
					])}
				`, "info")}
				${card("Recommended sequence", orderedList([
					"Load the DocType.",
					"Review the imported layout for missing or noisy fields.",
					"Clean up labels and fieldnames.",
					"Add tabs and sections only where the form will be easier to use.",
					"Save the template and preview it before sharing it with users.",
				]))}
			`,
		},
		standalone: {
			nav: "Standalone form",
			navSummary: "Build a standalone form",
			eyebrow: "Builder usage",
			title: "Create a standalone form from scratch",
			summary: "Use this mode when the form will be rendered in the viewer and does not need to live inside another DocType.",
			content: `
				<p class="afb-docs-lead">
					Standalone forms are stored as <strong>Form</strong> templates.
					They are ideal for surveys, application forms, intake flows, checklists, and any document that should live outside an existing ERP DocType.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Main workspace", list([
						"<strong>Canvas</strong> holds sections, columns, and fields.",
						"<strong>Property panel</strong> edits the currently selected item.",
						"<strong>Preview</strong> shows the rendered form before you save.",
						"<strong>Menu</strong> exposes Load Form, Load Doctype Form, Add via AI Agent, Create DocType, New Form, Preview, and Reload.",
					]))}
					${card("Field design rules", list([
						"Keep fieldnames lowercase snake_case and unique.",
						"Special characters are stripped from fieldnames during save and DocType creation.",
						"Select, Radio, Link, Dynamic Link, Table, and Mixed Table need extra configuration.",
						"Use tabs only when the form naturally breaks into larger groups.",
						"Use columns to make scanning easier, not just to fill space.",
					]))}
				</div>
				${table(
					["Supported field family", "Notes"],
					[
						["Data, Small Text, Long Text, Text Editor", "General purpose inputs for most records."],
						["Check, Date, Datetime, Time, Number, Percent", "Use the type that matches the data you need."],
						["Select, Radio", "Provide newline-separated options."],
						["Link, Dynamic Link", "Set the target DocType in the options field."],
						["Table, Mixed Table", "Define table columns, and rows when you need a mixed table layout."],
					]
				)}
				${callout("Preview and save", `
					<p>
						Preview before saving major changes.
						The builder stores the schema in JSON, so the preview is the fastest way to catch label problems, missing options, or a layout that feels too dense.
					</p>
				`, "brand")}
			`,
		},
		create_doctype: {
			nav: "Create DocType",
			navSummary: "Generate a real DocType",
			eyebrow: "Builder action",
			title: "Turn a saved form into a DocType",
			summary: "Use this when a builder form should become a real Frappe DocType that other workflows can use directly.",
			content: `
				<p class="afb-docs-lead">
					The builder normally keeps templates lightweight and JSON-backed.
					When you need a physical DocType, the new <strong>Create DocType</strong> action converts the saved schema into a standard Frappe DocType using the current builder fields.
				</p>
				<div class="afb-docs-grid two-up">
					${card("How to use it", orderedList([
						"Save the template first so the latest canvas state is on the server.",
						"Click <strong>Create DocType</strong> beside <strong>Save Changes</strong>.",
						"Enter the DocType name and choose the target module from <strong>Module Def</strong>.",
						"Confirm the dialog and let the app create the DocType from the saved schema.",
						"Open the created DocType in Desk if you want to review or extend it further.",
					]))}
					${card("What the creator does", list([
						"Only users with the <strong>System Manager</strong> role see and can use the button.",
						"The service sanitizes fieldnames and layout labels before Frappe sees them.",
						"Table and mixed table fields are mapped into proper child table structures.",
						"The DocType is created through Frappe's document API, not by direct SQL insertion.",
					]))}
				</div>
				${callout("Naming and safety", `
					<p>
						Special characters such as <code>&amp;</code> are stripped from fieldnames during save and creation.
						If the final DocType name needs a cleanup pass, the service normalizes it before insertion so the record stays Frappe-safe.
					</p>
				`, "warning")}
			`,
		},
		integration: {
			nav: "Subform integration",
			navSummary: "Embed in a DocType",
			eyebrow: "Embedded form",
			title: "Add a subform using Doctype Integration",
			summary: "Use integration mode when the form should appear as a reusable tab inside another DocType record.",
			content: `
				<p class="afb-docs-lead">
					The integration flow is the right choice when you want a form to behave like a subform inside a parent document.
					When the template is saved, the app generates a shared integration tab, a form selector, an embedded viewer, and a submission reference on the target DocType.
				</p>
				<div class="afb-docs-grid two-up">
					${card("How to set it up", orderedList([
						"Open the builder or load a DocType form first.",
						"Set <strong>Form Type</strong> to <strong>Doctype Integration</strong>.",
						"Choose the <strong>Target DocType</strong>.",
						"Design the embedded form fields and save the template.",
						"Open a saved parent document to see the integration tab.",
					]))}
					${card("What appears on the target DocType", list([
						"A reusable <strong>Ampower Form Integration</strong> tab.",
						"A <strong>Select Form</strong> link filtered to active integration templates for that DocType.",
						"An embedded form view area.",
						"A read-only <strong>Submission Reference</strong> link to the saved submission.",
						"An <strong>Autofill Subform</strong> action that opens the AI autofill flow for the embedded viewer.",
					]))}
				</div>
				${callout("Important behavior", `
					<p>
						The parent document must be saved before the embedded viewer can show the integration fields.
						The client script hides the integration tab on a new, unsaved parent record, so save the document once before expecting the subform to appear.
					</p>
				`, "warning")}
				${card("Release flow", list([
					"Save the integration template.",
					"Open the target DocType in Desk.",
					"Pick the active integration form from the selector.",
					"Fill the subform and save the parent document.",
					"The submission is stored in <strong>Dynamic Form Submission</strong> and linked back to the parent record.",
					"Later, use <strong>Autofill Subform</strong> to prefill the same embedded form from a PDF or image.",
				]))}
			`,
		},
		print_builder: {
			nav: "Print Builder",
			navSummary: "Design PDF layouts",
			eyebrow: "Print formats",
			title: "Design print formats for PDF output",
			summary: "Use the print builder when a saved form needs a custom PDF layout with repeatable header and footer regions.",
			content: `
				<p class="afb-docs-lead">
					The print builder is the companion page for <strong>Dynamic Print Format</strong>.
					It lets you place fields, tables, and matrix blocks on a page-sized canvas, then save that layout for PDF generation.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Where to open it", list([
						"Open the Desk page <code>/app/print-builder</code>.",
						"Choose a <strong>Dynamic Form Template</strong> first.",
						"Pick or create a <strong>Dynamic Print Format</strong> for that template.",
						"Use the page width, page height, and margin inputs to match the target paper size.",
					]))}
					${card("How the layout works", list([
						"Body items render in the main report flow.",
						"Header and footer regions are extracted separately for PDF output.",
						"Tables and mixed tables render using the selected print columns.",
						"Matrix blocks can be used for repeated boxes, signatures, labels, or compact report areas.",
					]))}
				</div>
				${callout("Preview and PDF", `
					<p>
						The preview uses the same normalized layout data as the saved format.
						When the user clicks PDF, the backend extracts the header and footer blocks and passes them to the PDF renderer as repeatable sections.
					</p>
				`, "brand")}
				${card("Good habits", orderedList([
					"Keep the header and footer widths aligned with the body margins.",
					"Use repeatable header/footer regions only for content that should appear on every page.",
					"Save the format and test the PDF output after any margin or table change.",
				]))}
			`,
		},
		ai_draft: {
			nav: "AI draft",
			navSummary: "Create draft from files",
			eyebrow: "AI assist",
			title: "Auto-create a form with AI",
			summary: "Use the builder menu to upload a PDF or image and let the app draft a schema from the OCR result.",
			content: `
				<p class="afb-docs-lead">
					AI drafting lives inside the builder under <strong>Add via AI Agent</strong>.
					The workflow is designed for form-like documents and report layouts where headings, labels, and table regions are visible in the source file.
				</p>
				<div class="afb-docs-grid three-up">
					${card("Step 1", `<p>Upload a PDF or image. The current implementation accepts PDFs and common image formats, with a PDF page limit of <strong>5 pages</strong>.</p>`)}
					${card("Step 2", `<p>The backend rasterizes pages and sends them to <strong>Google Vision</strong> for OCR before the model sees the content.</p>`)}
					${card("Step 3", `<p><strong>OpenAI</strong> converts the OCR into a builder-ready schema and returns warnings when anything is ambiguous.</p>`)}
				</div>
				${table(
					["Behavior", "What to expect"],
					[
						["Prompting", "The AI draft uses the system prompt from <strong>Form Builder Config</strong> when provided, otherwise it falls back to the built-in prompt."],
						["Structure", "Tabs, sections, columns, and tables are preserved when the OCR makes them obvious."],
						["Review", "The AI result is applied to the canvas, but you should still check labels, table columns, and fieldnames before saving."],
						["Warnings", "Any ambiguous items are surfaced so you can review them before publishing the form."],
					]
				)}
				${callout("Best practice", `
					<p>
						Use AI draft as a fast starting point, not as the final source of truth.
						A quick human review usually catches field names, sequence order, and table structure that need cleanup.
					</p>
				`, "brand")}
			`,
		},
		ai_autofill: {
			nav: "AI autofill",
			navSummary: "Prefill saved forms",
			eyebrow: "Viewer assist",
			title: "Autofill a saved form with AI",
			summary: "Upload a PDF or image in the viewer and let the app map the OCR text into the current template fields.",
			content: `
				<p class="afb-docs-lead">
					AI autofill lives in the <strong>Form Viewer</strong>.
					It reads the uploaded document, maps the OCR text to the current template, and places the values into the form so the user can review them before submitting.
				</p>
				<div class="afb-docs-grid two-up">
					${card("How it works", list([
						"Open <code>/app/form-viewer?template=&lt;template-name&gt;</code>.",
						"Load a saved template.",
						"Choose <strong>Autofill with AI</strong>.",
						"Upload a PDF or image and wait for the background job to finish.",
						"Review the values and submit only after checking the result.",
					]))}
					${card("Mapping rules", list([
						"The model only uses fieldnames that already exist in the template.",
						"Dates, datetimes, times, checks, and tables are normalized into stable JSON-friendly values.",
						"Unknown fields stay blank instead of being guessed.",
						"Table values come back as row objects keyed by the table column fieldnames.",
					]))}
				</div>
				${callout("Review before submit", `
					<p>
						Autofill saves time, but the user still owns the final result.
						Always review amounts, dates, names, and table rows before hitting submit.
					</p>
				`, "warning")}
				${callout("Embedded subforms", `
					<p>
						If the template is used as a Doctype Integration, the same AI autofill flow is also exposed on the parent document through <strong>Autofill Subform</strong>.
					</p>
				`, "brand")}
				${card("Prompt control", list([
					"The default autofill prompt is conservative and intentionally avoids guessing.",
					"If your records follow a repeatable structure, use the <strong>Autofill System Prompt</strong> field to teach the model the house style.",
					"The current code uses the same configured OpenAI key and OpenAI API URL as AI draft generation.",
				]))}
			`,
		},
		data: {
			nav: "Data model",
			navSummary: "Templates, submissions, config",
			eyebrow: "Storage",
			title: "Understand the data model and API surface",
			summary: "The app keeps a small footprint on purpose, which makes it easier to maintain and safer to ship as open source.",
			content: `
				<p class="afb-docs-lead">
					The codebase is deliberately small: one config DocType, one template DocType, and one submission DocType.
					Everything else happens through service code and Desk pages.
				</p>
				${table(
					["DocType", "Purpose"],
					[
						["<strong>Form Builder Config</strong>", "Stores the global AI keys, prompts, and report defaults."],
						["<strong>Dynamic Form Template</strong>", "Stores the JSON schema plus form name, type, active state, version, and target DocType."],
						["<strong>Dynamic Form Submission</strong>", "Stores the submitted JSON data and optional parent record reference."],
					]
				)}
				<div class="afb-docs-grid two-up">
					${card("Whitelisted APIs", list([
						"<code>get_form_schema</code>",
						"<code>save_form_template</code>",
						"<code>get_doctype_fields</code>",
						"<code>save_submission</code>",
						"<code>get_submissions</code>",
						"<code>enqueue_ai_form_builder_import</code>",
						"<code>enqueue_ai_form_autofill</code>",
					]))}
					${card("Useful caches", list([
						"Template schema cache for builder loads.",
						"Active template cache for selectors.",
						"Redis-backed job state for AI import and autofill progress.",
					]))}
				</div>
				${callout("Why this matters", `
					<p>
						When users understand the storage model, they stop expecting a new DocType for every form.
						That keeps implementations cleaner and reduces upgrade pain later.
					</p>
				`, "brand")}
			`,
		},
		troubleshooting: {
			nav: "Troubleshoot",
			navSummary: "Fix common issues",
			eyebrow: "Common issues",
			title: "Troubleshoot setup and usage problems",
			summary: "Use this before escalating an issue. Most problems are caused by missing config, stale assets, or a saved document that has not been refreshed yet.",
			content: `
				<p class="afb-docs-lead">
					Most support cases fall into a small number of buckets.
					Check the matching problem below before assuming the app is broken.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Builder page is blank", list([
						"Rebuild assets with <code>bench build --app ampower_form_builder</code>.",
						"Clear cache with <code>bench --site &lt;your-site&gt; clear-cache</code>.",
						"Restart bench and hard refresh the browser.",
					]))}
					${card("AI import or autofill errors", list([
						"Check <strong>OpenAI API Key</strong> and <strong>Google Service Account JSON</strong>.",
						"Confirm the Google JSON is a valid object and includes <code>client_email</code> and <code>private_key</code>.",
						"Make sure the uploaded file is a PDF or a supported image format.",
					]))}
				</div>
				<div class="afb-docs-grid two-up">
					${card("Integration tab does not show", list([
						"Confirm the template <strong>Form Type</strong> is <strong>Doctype Integration</strong>.",
						"Confirm <strong>Target DocType</strong> is set.",
						"Save the template again so the client script is regenerated.",
						"Open a saved parent document, not a new unsaved one.",
					]))}
					${card("Create DocType button is missing", list([
						"Confirm your user has the <strong>System Manager</strong> role.",
						"Refresh the page after any role change.",
						"Remember that the button is hidden for non-admin users by design.",
					]))}
					${card("Imported DocType looks incomplete", list([
						"Some DocType fields are intentionally skipped during import.",
						"Add the missing pieces manually after the import.",
						"Review child table mappings and field types before saving the final template.",
					]))}
				</div>
				${card("Report or viewer looks stale", list([
					"Refresh the page after saving the template.",
					"Check that the template is active.",
					"If you changed source code, rebuild the app bundle and restart the bench.",
				]))}
			`,
		},
		develop: {
			nav: "Developer notes",
			navSummary: "Build and release",
			eyebrow: "Open source",
			title: "Developer notes and release checklist",
			summary: "A quick reference for contributors or site admins who need to touch the codebase and ship it safely.",
			content: `
				<p class="afb-docs-lead">
					The repository is organized so the page controllers, service layer, and Vue builder stay separated.
					That makes it easier to patch the UI without accidentally changing the storage or AI behavior.
				</p>
				<div class="afb-docs-grid two-up">
					${card("Key routes", list([
						"<code>/app/form-builder</code> for the builder.",
						"<code>/app/form-viewer?template=&lt;template-name&gt;</code> for the viewer.",
						"<code>/app/print-builder</code> for print format design.",
						"<code>/app/form-builder-docs</code> for this guide.",
					]))}
					${card("Common commands", list([
						"<code>bench build --app ampower_form_builder</code>",
						"<code>bench restart</code>",
						"<code>bench --site &lt;your-site&gt; clear-cache</code>",
					]))}
				</div>
				${callout("Release checklist", `
					${list([
						"Verify the docs page still opens and the sidebar works on mobile.",
						"Test one standalone form and one integration template.",
						"Test the Create DocType flow as a System Manager and confirm the created DocType opens.",
						"Test AI draft and AI autofill with a small sample file.",
						"Confirm the config record has the right prompts and credentials.",
						"Run a full round-trip from builder to viewer to submission.",
					])}
				`, "warning")}
			`,
		},
	};

	const navOrder = [
		"overview",
		"permissions",
		"config",
		"import_doctype",
		"standalone",
		"create_doctype",
		"integration",
		"print_builder",
		"ai_draft",
		"ai_autofill",
		"data",
		"troubleshooting",
		"develop",
	];

	const initialSectionKey = "overview";
	const currentSection = () => sections[initialSectionKey];

	const injectStyles = () => {
		if (document.getElementById("afb-form-builder-docs-style")) {
			return;
		}

		const style = document.createElement("style");
		style.id = "afb-form-builder-docs-style";
		style.textContent = `
			.form-builder-docs-page .page-head,
			.form-builder-docs-page .page-form,
			.form-builder-docs-page .layout-side-section {
				display: none !important;
			}

			.form-builder-docs-page .layout-main-section-wrapper,
			.form-builder-docs-page .layout-main-section {
				height: 100%;
			}

			.form-builder-docs-page .page-body {
				padding-top: 0;
				background:
					radial-gradient(circle at top left, rgba(99, 102, 241, 0.1), transparent 34%),
					radial-gradient(circle at top right, rgba(45, 212, 191, 0.08), transparent 28%),
					linear-gradient(180deg, #f8faff 0%, #f3f6ff 42%, #eef3ff 100%);
			}

			.afb-docs-container {
				box-sizing: border-box;
				height: calc(100vh - var(--navbar-height, 48px));
				padding: 18px;
				color: #172033;
				font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
				display: flex;
				flex-direction: column;
				overflow: hidden;
				position: relative;
			}

			.afb-docs-hero {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 18px;
				padding: 12px 18px;
				border: 1px solid rgba(99, 102, 241, 0.12);
				border-radius: 24px;
				height: 13vh;
				min-height: 88px;
				max-height: 160px;
				overflow: hidden;
				background:
					linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(247, 249, 255, 0.96)),
					radial-gradient(circle at top right, rgba(99, 102, 241, 0.14), transparent 34%);
				box-shadow: 0 22px 60px rgba(15, 23, 42, 0.08);
			}

			.afb-docs-kicker {
				display: inline-flex;
				align-items: center;
				gap: 8px;
				margin-bottom: 6px;
				padding: 5px 9px;
				border-radius: 999px;
				background: rgba(99, 102, 241, 0.1);
				color: #4f46e5;
				font-size: 11px;
				font-weight: 700;
				letter-spacing: 0.12em;
				text-transform: uppercase;
			}

			.afb-docs-hero h1,
			.afb-docs-detail h2 {
				margin: 0;
				color: #111827;
				letter-spacing: -0.03em;
			}

			.afb-docs-hero h1 {
				font-size: clamp(1.4rem, 2vw, 2rem);
				line-height: 1.08;
				max-width: none;
			}

			.afb-docs-hero-summary,
			.afb-docs-summary {
				margin: 6px 0 0;
				color: #52607a;
				font-size: 0.9rem;
				line-height: 1.45;
				max-width: 74ch;
			}

			.afb-docs-layout {
				display: flex;
				gap: 18px;
				margin-top: 12px;
				align-items: stretch;
				min-height: 0;
				flex: 1;
				overflow: hidden;
			}

			.afb-docs-sidebar {
				width: 314px;
				min-width: 314px;
				flex: 0 0 314px;
				height: 100%;
				overflow-y: auto;
				padding: 16px;
				border: 1px solid rgba(99, 102, 241, 0.12);
				border-radius: 20px;
				background:
					radial-gradient(circle at top, rgba(99, 102, 241, 0.08), transparent 36%),
					linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 249, 255, 0.98));
				backdrop-filter: blur(12px);
				box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
			}

			.afb-docs-sidebar-title {
				margin: 0 0 12px;
				color: #111827;
				font-size: 14px;
				font-weight: 700;
				letter-spacing: 0.04em;
				text-transform: uppercase;
			}

			.afb-docs-nav {
				display: grid;
				gap: 8px;
			}

			.afb-docs-section {
				display: grid;
				grid-template-columns: 32px minmax(0, 1fr);
				gap: 12px;
				align-items: start;
				padding: 11px 12px;
				border: 1px solid transparent;
				border-radius: 16px;
				background: transparent;
				color: #334155;
				text-align: left;
				transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
			}

			.afb-docs-section:hover {
				background: rgba(99, 102, 241, 0.08);
				transform: translateX(2px);
			}

			.afb-docs-section.active {
				border-color: rgba(99, 102, 241, 0.22);
				background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(45, 212, 191, 0.08));
				box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.08);
			}

			.afb-docs-section-index {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 32px;
				height: 32px;
				border-radius: 999px;
				background: rgba(99, 102, 241, 0.12);
				color: #4f46e5;
				font-size: 12px;
				font-weight: 800;
			}

			.afb-docs-section h3 {
				margin: 0;
				color: #111827;
				font-size: 14px;
				line-height: 1.35;
			}

			.afb-docs-section p {
				margin: 4px 0 0;
				color: #64748b;
				font-size: 12px;
				line-height: 1.5;
			}

			.afb-docs-mobile-toolbar {
				display: none;
				margin: 18px 0 0;
			}

			.afb-docs-sidebar-toggle {
				display: inline-flex;
				align-items: center;
				gap: 8px;
				padding: 10px 14px;
				border-radius: 12px;
				border: 1px solid rgba(99, 102, 241, 0.14);
				background: rgba(255, 255, 255, 0.9);
				color: #1f2937;
				box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
			}

			.afb-docs-backdrop {
				display: none;
			}

			.afb-docs-main {
				min-width: 0;
				flex: 1;
				height: 100%;
				overflow-y: auto;
				padding-right: 4px;
			}

			.afb-docs-detail {
				padding: 20px;
				border: 1px solid rgba(99, 102, 241, 0.12);
				border-radius: 22px;
				background: rgba(255, 255, 255, 0.92);
				backdrop-filter: blur(12px);
				box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
			}

			.afb-docs-detail-header {
				display: grid;
				gap: 8px;
				margin-bottom: 12px;
			}

			.afb-docs-eyebrow {
				display: inline-flex;
				align-items: center;
				width: fit-content;
				padding: 6px 10px;
				border-radius: 999px;
				background: rgba(99, 102, 241, 0.1);
				color: #4f46e5;
				font-size: 12px;
				font-weight: 700;
				letter-spacing: 0.12em;
				text-transform: uppercase;
			}

			.afb-docs-detail h2 {
				font-size: clamp(1.2rem, 1.7vw, 1.65rem);
				line-height: 1.14;
			}

			.afb-docs-detail .afb-docs-summary {
				margin-top: 0;
				font-size: 13px;
			}

			.afb-docs-content {
				display: grid;
				gap: 14px;
			}

			.afb-docs-lead,
			.afb-docs-note {
				margin: 0;
				color: #334155;
				font-size: 15px;
				line-height: 1.8;
			}

			.afb-docs-note {
				font-size: 13px;
				color: #64748b;
			}

			.afb-docs-grid {
				display: grid;
				gap: 14px;
			}

			.afb-docs-grid.two-up {
				grid-template-columns: repeat(2, minmax(0, 1fr));
			}

			.afb-docs-grid.three-up {
				grid-template-columns: repeat(3, minmax(0, 1fr));
			}

			.afb-docs-card,
			.afb-docs-callout {
				padding: 16px;
				border-radius: 18px;
				border: 1px solid rgba(99, 102, 241, 0.12);
				background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 249, 255, 0.96));
				box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
			}

			.afb-docs-card.is-brand,
			.afb-docs-callout.is-brand {
				background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(45, 212, 191, 0.08));
			}

			.afb-docs-card.is-warning,
			.afb-docs-callout.is-warning {
				background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(251, 191, 36, 0.08));
			}

			.afb-docs-card h3,
			.afb-docs-callout h4 {
				margin: 0 0 10px;
				color: #111827;
				font-size: 16px;
				line-height: 1.35;
			}

			.afb-docs-callout h4 {
				font-size: 15px;
			}

			.afb-docs-card-body,
			.afb-docs-callout-body {
				color: #475569;
				font-size: 14px;
				line-height: 1.75;
			}

			.afb-docs-card-body > :first-child,
			.afb-docs-callout-body > :first-child {
				margin-top: 0;
			}

			.afb-docs-card-body > :last-child,
			.afb-docs-callout-body > :last-child {
				margin-bottom: 0;
			}

			.afb-docs-list {
				margin: 0;
				padding-left: 18px;
				color: #334155;
			}

			.afb-docs-list li + li {
				margin-top: 8px;
			}

			.afb-docs-list code,
			.afb-docs-table code {
				padding: 0.1rem 0.35rem;
				border-radius: 6px;
				background: rgba(99, 102, 241, 0.1);
				color: #4338ca;
			}

			.afb-docs-code {
				overflow: auto;
				margin: 12px 0 0;
				padding: 14px 16px;
				border-radius: 16px;
				border: 1px solid rgba(99, 102, 241, 0.12);
				background: #0f172a;
				color: #e2e8f0;
				font-size: 13px;
				line-height: 1.65;
			}

			.afb-docs-table-wrap {
				overflow: auto;
				border: 1px solid rgba(99, 102, 241, 0.12);
				border-radius: 16px;
				background: rgba(255, 255, 255, 0.96);
				box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
			}

			.afb-docs-table {
				width: 100%;
				border-collapse: collapse;
				min-width: 640px;
			}

			.afb-docs-table th,
			.afb-docs-table td {
				padding: 12px 14px;
				border-bottom: 1px solid rgba(226, 232, 240, 0.9);
				vertical-align: top;
				color: #334155;
				font-size: 14px;
				line-height: 1.6;
			}

			.afb-docs-table th {
				background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(45, 212, 191, 0.06));
				color: #1e293b;
				font-weight: 700;
				text-align: left;
			}

			.afb-docs-table tr:last-child td {
				border-bottom: none;
			}

			.afb-docs-table td strong,
			.afb-docs-table th strong {
				color: #111827;
			}

			.afb-docs-table td code {
				padding: 0.1rem 0.35rem;
				border-radius: 6px;
				background: rgba(99, 102, 241, 0.1);
				color: #4338ca;
			}

			.afb-docs-note-inline {
				display: block;
				margin-top: 10px;
				color: #64748b;
				font-size: 12px;
				line-height: 1.6;
			}

			.afb-docs-section .btn {
				box-shadow: none;
			}

			@media (max-width: 1120px) {
				.afb-docs-hero,
				.afb-docs-layout,
				.afb-docs-grid.two-up,
				.afb-docs-grid.three-up {
					grid-template-columns: 1fr;
				}
				.afb-docs-sidebar {
					width: 100%;
					min-width: 0;
					flex: 1 1 auto;
					height: auto;
					overflow: visible;
				}
			}

			@media (max-width: 900px) {
				.form-builder-docs-page .page-body {
					background:
						radial-gradient(circle at top left, rgba(99, 102, 241, 0.1), transparent 34%),
						linear-gradient(180deg, #f8faff 0%, #eef3ff 100%);
				}

				.afb-docs-container {
					padding: 14px;
					height: auto;
					overflow: visible;
				}

				.afb-docs-hero {
					padding: 12px 14px;
					height: auto;
					max-height: none;
					overflow: visible;
				}

				.afb-docs-mobile-toolbar {
					display: block;
				}

				.afb-docs-layout {
					display: block;
					height: auto;
					overflow: visible;
				}

				.afb-docs-sidebar {
					position: fixed;
					left: 14px;
					right: 14px;
					top: 82px;
					z-index: 120;
					max-height: calc(100vh - 110px);
					overflow: auto;
					transform: translateY(12px);
					opacity: 0;
					pointer-events: none;
					transition: transform 0.18s ease, opacity 0.18s ease;
					width: auto;
					min-width: 0;
				}

				.afb-docs-container.sidebar-open .afb-docs-sidebar {
					transform: translateY(0);
					opacity: 1;
					pointer-events: auto;
				}

				.afb-docs-backdrop {
					display: block;
					position: fixed;
					inset: 0;
					z-index: 110;
					background: rgba(15, 23, 42, 0.24);
					backdrop-filter: blur(4px);
					opacity: 0;
					pointer-events: none;
					transition: opacity 0.18s ease;
				}

				.afb-docs-container.sidebar-open .afb-docs-backdrop {
					opacity: 1;
					pointer-events: auto;
				}

				.afb-docs-detail {
					padding: 18px;
				}
			}
		`;
		document.head.appendChild(style);
	};

	const renderSectionNav = () =>
		navOrder
			.map((key, index) => {
				const section = sections[key];
				return `
					<button type="button" class="afb-docs-section${key === initialSectionKey ? " active" : ""}" data-section="${key}">
						<span class="afb-docs-section-index">${index + 1}</span>
						<span>
							<h3>${section.nav}</h3>
							<p>${section.navSummary || section.summary}</p>
						</span>
					</button>
				`;
			})
			.join("");

	const renderShell = () => {
		const summary = currentSection().summary;
		return `
			<div class="afb-docs-container">
				<section class="afb-docs-hero">
					<div class="afb-docs-hero-copy">
						<div class="afb-docs-kicker">AmPower Form Builder</div>
						<h1>Setup, Import, Integrate & Automate Forms</h1>
					</div>
				</section>

				<div class="afb-docs-mobile-toolbar">
					<button type="button" class="btn btn-default afb-sidebar-toggle" aria-expanded="false" aria-controls="afb-docs-sidebar">
						Sections
					</button>
				</div>

				<div class="afb-docs-layout">
					<aside id="afb-docs-sidebar" class="afb-docs-sidebar">
						<div class="afb-docs-sidebar-title">Documentation map</div>
						<nav class="afb-docs-nav">${renderSectionNav()}</nav>
					</aside>
					<div class="afb-docs-backdrop"></div>
					<main class="afb-docs-main">
						<div id="afb-docs-detail-view" class="afb-docs-detail" data-section="${initialSectionKey}">
							<div class="afb-docs-detail-header">
								<div class="afb-docs-eyebrow">${currentSection().eyebrow}</div>
								<h2>${currentSection().title}</h2>
								<p class="afb-docs-summary">${summary}</p>
							</div>
							<div class="afb-docs-content">${currentSection().content}</div>
						</div>
					</main>
				</div>
			</div>
		`;
	};

	$(wrapper).find(".layout-main-section").html(renderShell());
	injectStyles();

	const $container = $(wrapper).find(".afb-docs-container");
	const $detail = $(wrapper).find("#afb-docs-detail-view");

	const openMobileSidebar = () => {
		$container.addClass("sidebar-open");
		$container.find(".afb-sidebar-toggle").attr("aria-expanded", "true");
	};

	const closeMobileSidebar = () => {
		$container.removeClass("sidebar-open");
		$container.find(".afb-sidebar-toggle").attr("aria-expanded", "false");
	};

	const updateDetailView = (sectionKey) => {
		const section = sections[sectionKey];
		if (!section) return;

		const renderHtml = `
			<div class="afb-docs-detail-header">
				<div class="afb-docs-eyebrow">${section.eyebrow}</div>
				<h2>${section.title}</h2>
				<p class="afb-docs-summary">${section.summary}</p>
			</div>
			<div class="afb-docs-content">${section.content}</div>
		`;

		const $view = $("#afb-docs-detail-view");
		$view.stop(true, true).fadeOut(120, function () {
			$view
				.html(renderHtml)
				.attr("data-section", sectionKey)
				.fadeIn(120);
		});

		$(".afb-docs-section").removeClass("active");
		$(`.afb-docs-section[data-section="${sectionKey}"]`).addClass("active");
		closeMobileSidebar();
	};

	$(wrapper).off(".formBuilderDocs");
	$(wrapper).on("click.formBuilderDocs", ".afb-docs-section", function () {
		updateDetailView($(this).data("section"));
	});

	$(wrapper).on("click.formBuilderDocs", ".afb-sidebar-toggle", function () {
		if ($container.hasClass("sidebar-open")) {
			closeMobileSidebar();
			return;
		}

		openMobileSidebar();
	});

	$(wrapper).on("click.formBuilderDocs", ".afb-docs-backdrop", function () {
		closeMobileSidebar();
	});

	$(window).off("resize.formBuilderDocs").on("resize.formBuilderDocs", function () {
		if (window.innerWidth > 900) {
			closeMobileSidebar();
		}
	});

	updateDetailView(initialSectionKey);
};
