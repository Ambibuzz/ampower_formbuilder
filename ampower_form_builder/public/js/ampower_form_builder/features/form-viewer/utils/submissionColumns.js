const SYSTEM_FIELDS = new Set([
	"name",
	"status",
	"modified",
	"submitted_on",
	"owner",
	"_name",
	"_status",
	"_submitted_on",
	"_owner",
]);

function isTruthyFlag(value) {
	return value === true || value === 1 || value === "1";
}

export function normalizeSubmissionListColumn(column = {}) {
	const fieldname = String(column.fieldname || column.field_name || "").trim();
	const label = String(column.label || column.field_label || fieldname || "").trim();
	return {
		fieldname,
		label: label || fieldname,
		fieldtype: column.fieldtype || column.field_type || "Data",
		showInList: isTruthyFlag(column.in_list_view) || isTruthyFlag(column.show_in_list_view) || isTruthyFlag(column.list_view),
	};
}

export function buildSubmissionListColumns(columns = [], { maxVisible = 2 } = {}) {
	const normalized = columns.map(normalizeSubmissionListColumn).filter((column) => column.fieldname || column.label);
	const explicit = normalized.filter((column) => column.showInList && !SYSTEM_FIELDS.has(column.fieldname));
	const preferred = explicit.length ? explicit : normalized.filter((column) => !SYSTEM_FIELDS.has(column.fieldname));
	const limited = preferred.slice(0, Math.max(1, maxVisible));

	if (limited.length) {
		return limited;
	}

	return [
		{
			fieldname: "",
			label: __("Naming series"),
			fieldtype: "Data",
			showInList: true,
		},
	];
}



