# AmPower Form Builder

AmPower Form Builder is a schema-driven form builder for Frappe/ERPNext. It lets you design forms visually, store the form definition as JSON, render those forms dynamically, capture submissions, optionally integrate a form directly into an existing DocType, and create a real DocType from a saved builder form when you need one.

## What It Includes

- Vue-based drag-and-drop form builder page at `/app/form-builder`
- Dynamic form viewer page at `/app/form-viewer?template=<template-name>`
- Dedicated print builder page for `Dynamic Print Format`
- In-app docs page at `/app/form-builder-docs`
- AI-assisted form drafting from PDF/image files in the builder
- AI autofill from PDF/image files in the viewer
- AI autofill for embedded subforms inside a target DocType
- DocType import flow from the builder menu
- DocType creation flow from the builder for System Managers
- Doctype integration flow for embedding a form inside a target DocType
- JSON-backed template storage in `Dynamic Form Template`
- Submission storage in `Dynamic Form Submission`
- Server-side APIs for saving templates, loading schemas, and listing submissions

## Data Model

This app keeps the footprint intentionally small:

- `Dynamic Form Template`: stores form metadata, form type, target DocType, active state, version, description, and the full JSON schema
- `Dynamic Form Submission`: stores submitted data as JSON against a template, with optional reference back to a parent DocType record
- `Form Builder Config`: app-level configuration DocType used by the module

This means you can support many forms without polluting the system with one DocType per form, while still allowing selected forms to live inside an existing DocType when needed.

## Print Builder

AmPower Form Builder also ships a dedicated print-format editor in the same app.

It is built for `Dynamic Print Format` records and is separate from the form builder and form viewer screens.

Typical workflow:

- open the Desk page `Print Builder`
- choose a `Dynamic Form Template`
- place fields, tables, and matrix blocks on the page canvas
- use the header and footer regions for repeatable PDF sections
- save the layout to `Dynamic Print Format`

The editor, preview, and PDF renderer all use the same normalized layout structure. When a PDF is generated, the backend extracts the header and footer blocks and passes them to `wkhtmltopdf` as repeatable sections.

## Features

- Schema-driven forms with normalized field metadata
- Section and column based layouts
- Tab-based layouts for larger forms
- Load an existing DocType and start from its field structure
- Use `Add via AI Agent` to draft a form from a PDF or image
- Use `Autofill with AI` to prefill a saved form template from a PDF or image
- Use `Create DocType` to turn a saved builder form into a real Frappe DocType
- Choose between standalone `Form` and `Doctype Integration` templates
- Embed a selected form into a target DocType using a shared integration tab
- Dynamic rendering from stored JSON schema
- Submission listing with columns inferred from the saved schema
- Print format authoring with page margins, headers, footers, and matrix-based layout blocks
- SaaS-friendly architecture with a minimal DocType surface area

## Installation

From your bench:

```bash
bench get-app ampower_form_builder
bench --site <your-site> install-app ampower_form_builder
bench --site <your-site> migrate
```

If the app is already present in `apps/`, install it on the site:

```bash
bench --site <your-site> install-app ampower_form_builder
bench --site <your-site> migrate
```

## Usage

### Before You Start

Make sure:

- `ampower_form_builder` is installed on your site
- you have access to the AmPower Form Builder page
- frontend assets are built and loading correctly
- `Form Builder Config` has your `OpenAI API Key`, `OpenAI API URL`, and `Google Service Account JSON` set up
- optional prompts are configured if you want to customize the AI flows:
  - `Form Builder System Prompt`
  - `Autofill System Prompt`

### Documentation

If you want the in-app walkthrough instead of this README, open:

```text
/app/form-builder-docs
```

That page is written as a user-facing guide for installation, configuration, DocType import, DocType creation, form integration, AI draft generation, and AI autofill.

### 1. Open The Builder

Open the Desk route:

```text
/app/form-builder
```

The page opens the visual builder where you can design the form structure and save it as a `Dynamic Form Template`.

If you want AI help while building, use `Add via AI Agent` from the builder menu and upload a PDF or image. The app will draft a form from the document and place it on the canvas for review.

### 2. Create A Standalone Form

Use this when you want a form that lives on its own and is rendered in the Form Viewer.

#### Step 1: Start a new form

Click `New Form` from the builder menu, or let the page open with a blank layout.

#### Step 2: Enter the form details

Fill in:

- `Form Name`
- optional `Description`

Keep `Form Type` as `Form` for a standalone form.

#### Step 3: Build the layout

Add and organize:

- tabs
- sections
- columns
- fields

Use tabs to group larger forms into logical parts.

#### Step 4: Configure fields

Select any field to edit properties such as:

- label
- fieldname
- field type
- placeholder
- description
- default value
- required
- read only
- hidden
- depends on
- options

For these field types, provide the required extra setup:

- `Select` and `Radio`: define options
- `Link` and `Dynamic Link`: define the target DocType in `options`
- `Table`: define table columns
- `Mixed Table`: define table columns and rows

#### Step 5: Preview and save

Use `Preview` to verify the layout and behavior, then click `Save Changes`.

The template is stored as a `Dynamic Form Template`.

#### Step 6: View the form

Open the Form Viewer route:

```text
/app/form-viewer?template=<template-name>
```

Replace `<template-name>` with the `Dynamic Form Template` document name you want to render.

In the viewer, you can also use `Autofill with AI` from the menu to upload a PDF or image and prefill the current form with detected values. Review the values before you submit.
If the form is embedded inside a target DocType, the parent document also gets an `Autofill Subform` action that opens the same autofill flow for the subform.

### 3. Create A DocType From The Builder

Use this when you want the current builder schema to become a real Frappe DocType instead of staying template-backed.

#### Step 1: Save the template

Open the builder, finish the form layout, and save the template first. The create flow works from the saved builder schema.

#### Step 2: Click `Create DocType`

The button appears beside `Save Changes` only for users with the `System Manager` role.

#### Step 3: Fill the creation dialog

Enter:

- `DocType Name`
- `Module` linked to `Module Def`

The app sanitizes fieldnames and layout labels before sending them to Frappe, so special characters such as `&` are stripped automatically.

#### Step 4: Review the generated DocType

The app sends the current form schema to Frappe using the Document API, and Frappe creates the new DocType with the fields already defined in the builder.

If the creation succeeds, the builder opens the new DocType in Desk.

### 4. Create A Doctype Integration Form

Use this when you want the form to appear inside an existing DocType form page.

#### Step 1: Load a source DocType or start from scratch

You can either:

- open the builder and design manually, or
- use `Load Doctype Form` from the builder menu and select a DocType to import its fields

When you load a DocType, the builder converts its fields into the builder canvas so you can reuse them as a starting point.

#### Step 2: Set the form type

Change `Form Type` to `Doctype Integration`.

Once this is selected, the builder shows the `Target DocType` field.

#### Step 3: Select the target DocType

Choose the DocType where the form should be embedded.

Important rules:

- the target must be a real DocType
- the target cannot be a child table DocType
- the template must remain active for the integration to appear

If you loaded a DocType first, the builder can use that DocType as the target when you switch to integration mode.

#### Step 4: Design the embedded form

Add the sections, tabs, columns, and fields you want the target DocType to display.

The integration area on the target DocType will show:

- a form selector
- the embedded viewer
- the submission reference field

#### Step 5: Save the template

Save the template after confirming the `Form Type` and `Target DocType`.

On save, AmPower Form Builder syncs the target DocType with:

- a reusable `AmPower Form Integration` tab
- a `Select Form` link filtered to active integration templates for that DocType
- an embedded form viewer area
- a `Submission Reference` link to the saved submission

The integration tab is hidden on a brand-new unsaved parent record, so open and save the parent document once before expecting the embedded form to appear.

#### Step 6: Open the target DocType

Go to the target DocType in Desk and open a document.

You should see the `AmPower Form Integration` tab with the form selector.

Select the saved form template if it is not selected already.

#### Step 7: Fill and save the embedded form

Enter values in the embedded form and save the parent document.

When the embedded form is submitted:

- the data is saved in `Dynamic Form Submission`
- the parent document gets a `Submission Reference`
- the embedded viewer stays synchronized with the saved submission
- the parent document can later reopen the same subform through `Autofill Subform`

### 5. Edit An Existing Form

To edit a saved template:

1. Open the builder
2. Use `Load Form`
3. Select the `Dynamic Form Template`
4. Make your changes
5. Save again

If the template is a Doctype Integration form, the target DocType integration is refreshed on save.

### 6. Import A DocType As A Starting Point

If you already have a DocType and want to reuse its structure:

1. Open the builder
2. Use `Load Doctype Form`
3. Select the DocType
4. Review the imported fields
5. Adjust the layout and field properties

The importer preserves tabs, sections, columns, and child tables where possible, but intentionally skips fields that do not translate cleanly into the builder canvas such as HTML, Button, Image, Heading, Geolocation, and Signature.

## AI Workflows

### AI Draft Generation

Use `Add via AI Agent` from the builder menu when you want the app to draft a schema from a PDF or image.

The flow uses:

- Google Vision OCR for the uploaded file
- OpenAI structured output to draft the form schema
- the system prompt from `Form Builder Config` when provided

Current behavior:

- PDFs are limited to 5 pages in the import flow
- supported inputs are PDF and common image files
- the result is a draft that should be reviewed before saving

### AI Autofill

Use `Autofill with AI` from the viewer when you want to map a PDF or image to a saved template.
If the template is used as a `Doctype Integration`, you can also launch the same autofill flow from the parent DocType with `Autofill Subform`.

The flow uses:

- Google Vision OCR for the uploaded file
- OpenAI mapping against the currently loaded template
- the system prompt from `Form Builder Config` when provided

Current behavior:

- unknown values are left blank instead of being guessed
- dates, datetimes, times, checks, and tables are normalized for the form model
- the user should review the suggested values before submission
- save the result as either a standalone form or a Doctype Integration form

This is useful when you want to quickly bootstrap a form from an existing business document.

### Validation Notes

- `Form Name` is required
- fieldnames must be unique
- fieldnames should use lowercase letters, numbers, and underscores
- special characters in fieldnames and layout labels are stripped automatically during save and DocType creation
- `Select` and `Radio` fields require options
- `Link` fields require a target DocType in options
- `Table` fields require columns
- `Mixed Table` fields require columns and rows
- `Target DocType` is required when `Form Type` is `Doctype Integration`
- `Create DocType` is available only to users with the `System Manager` role

### Troubleshooting

#### The integration tab does not appear

Check that:

- the template is active
- the template `Form Type` is `Doctype Integration`
- the `Target DocType` is set correctly
- you saved the template after making changes

#### The imported DocType looks incomplete

Some DocType field types are intentionally skipped during import because they do not translate cleanly into the builder canvas.

You can review the imported layout and add the missing fields manually if needed.

#### The Create DocType button is missing

Only users with the `System Manager` role can see and use the button.

If you expect to create a DocType, confirm your user has that role and refresh the page after the role change.

#### Submission does not save

Make sure the form has valid fieldnames and that the target DocType record can be saved in Frappe.

If you changed frontend code recently, rebuild assets and clear cache.

### Useful Paths

- Builder: `/app/form-builder`
- Viewer: `/app/form-viewer?template=<template-name>`

## Developer Notes

### Frontend Assets

The builder UI depends on bundled frontend assets, including:

- `ampower_form_builder.bundle.js`
- `ampower_form_builder.bundle.css`

If you change frontend code, rebuild assets and restart the bench as needed for your environment.

Common commands:

```bash
bench build --app ampower_form_builder
bench restart
```

If you are developing locally with a running watcher, use your usual frontend build workflow instead.

## Troubleshooting

### Form Builder Page Does Not Load

If `/app/form-builder` opens but the UI does not mount correctly:

1. Rebuild frontend assets:

```bash
bench build --app ampower_form_builder
```

2. Clear cached assets if needed:

```bash
bench --site <your-site> clear-cache
```

3. Restart bench services:

```bash
bench restart
```

4. Refresh the browser with a hard reload.

This is usually caused by stale or missing bundled assets after frontend changes.

### Target DocType Integration Does Not Appear

If the integration tab does not show up on the target DocType:

1. Confirm the template `Form Type` is set to `Doctype Integration`.
2. Confirm `Target DocType` is set and the DocType exists.
3. Make sure the template is active.
4. Save the template again so the integration client script is regenerated.
5. Clear cache and refresh the target DocType form.

## License

MIT
