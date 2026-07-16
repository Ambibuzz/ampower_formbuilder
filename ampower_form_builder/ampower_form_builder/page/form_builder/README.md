# Form Builder Page

This page lets you create and manage dynamic forms in Ampower Form Builder.

For the full setup, AI, DocType import, and integration walkthrough, open:

```text
/app/form-builder-docs
```

Path:

```text
/app/form-builder
```

## What This Page Does

The Form Builder page is used to:

- create a new form template
- add sections, tabs, columns, and fields
- configure field properties
- preview the form before saving
- save the form as a `Dynamic Form Template`

The form structure is stored as JSON and later rendered by the Form Viewer page.

## Before You Start

Make sure:

- the app `ampower_form_builder` is installed on your site
- you have permission to access the page
- frontend assets are built and loading correctly
- `Form Builder Config` contains the OpenAI and Google Vision credentials used by the AI flows

## How To Open Form Builder

Open the Desk route:

```text
/app/form-builder
```

When the page loads, the Vue-based builder is mounted inside the page wrapper.

## Main Areas In The Builder

The page is usually used in these parts:

- Builder tabs: switch between tab sections in the form
- Canvas: shows sections, columns, and fields visually
- Property panel: edit the selected field or layout item
- Actions: save, preview, add fields, and manage layout

## Step-by-Step: Create A Form

### 1. Open the page

Go to `/app/form-builder`.

If you are creating a new form, start with a blank builder layout.

### 2. Add a section or tab

Use the section actions to add:

- a normal section
- a tab section

Tabs help split large forms into grouped steps or categories.

### 3. Add columns

Inside a section, add one or more columns.

Use columns when you want:

- side-by-side fields
- cleaner visual grouping
- better use of space for wide forms

### 4. Add fields

Inside a column, use the add field action to insert fields such as:

- Data
- Date
- Datetime
- Time
- Check
- Select
- Radio
- Link
- Long Text
- Small Text
- Table
- Mixed Table

Each field is added to the selected column in the canvas.

### 5. Edit field properties

Select a field in the canvas to open its properties.

Typical properties include:

- label
- fieldname
- fieldtype
- placeholder
- description
- default value
- required
- read only
- hidden
- depends on
- options

Important:

- `fieldname` must not be empty
- `fieldname` should start with a letter
- use lowercase letters, numbers, and underscores only
- avoid duplicate fieldnames

### 6. Configure Select, Radio, Link, and Table fields

Some field types need extra setup:

- `Select` and `Radio`: add options
- `Link` and `Dynamic Link`: define the target DocType in options
- `Table`: define table columns
- `Mixed Table`: define both table columns and table rows

For table-style fields, you can:

- add columns
- rename columns
- choose a column fieldtype
- mark columns as required
- add rows for mixed tables

### 7. Rearrange the layout

Use the drag handle to reorder:

- sections
- columns inside a section
- fields inside a column

This controls the visual order of the final form.

### 8. Preview the form

Open preview to check:

- the field order
- labels and descriptions
- tab grouping
- table fields
- overall form flow

Use preview before saving major changes.

### 9. Save the template

When the form is ready:

- enter the form title
- add an optional description
- save the template

Saving creates or updates a `Dynamic Form Template` record.

## Loading An Existing Template

Existing templates can be loaded into the builder and edited again.

When a template is loaded:

- the stored JSON schema is converted back into builder sections and fields
- the current template name, description, version, and active state are restored

## Output Of This Page

The Form Builder page saves a schema that includes:

- form name
- description
- flat field data
- section layout
- column grouping
- table configuration

This schema is later used by the Form Viewer page to render the actual form and store submissions.

## Good Practices

- keep labels clear and user-friendly
- keep fieldnames stable once submissions exist
- group related fields into sections or tabs
- use columns only when it improves readability
- preview before saving
- use table fields only when repeated structured data is needed

## Troubleshooting

### Builder page does not load

If the page opens but the builder does not appear:

```bash
bench build --app ampower_form_builder
bench --site <your-site> clear-cache
bench restart
```

Then hard refresh the browser.

### Bundle load error

If the page shows a form builder bundle error message, the frontend assets are missing, stale, or not built.

### Validation error while saving

Check for:

- empty form title
- empty fieldname
- duplicate fieldname
- invalid fieldname format
- missing options for Select or Radio
- missing DocType option for Link fields
- missing columns for Table or Mixed Table

## Related Records And Pages

- Page: `/app/form-builder`
- Viewer: `/app/form-viewer?template=<template-name>`
- DocType: `Dynamic Form Template`
- DocType: `Dynamic Form Submission`
