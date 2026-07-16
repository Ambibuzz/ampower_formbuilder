function get_viewer_context_from_route() {
	const route = frappe.get_route ? frappe.get_route() : [];
	const urlParams = new URLSearchParams(window.location.search);
	return {
		templateName: route[1] || urlParams.get("template") || "",
		submissionName: route[2] || urlParams.get("submission") || "",
	};
}

function sync_form_viewer_route(wrapper) {
	if (!wrapper.form_viewer) return;

	const route = frappe.get_route ? frappe.get_route() : [];
	if (route[0] !== "form_viewer") return;

	const context = get_viewer_context_from_route();
	wrapper.form_viewer.update({
		...context,
	});
}

frappe.pages["form_viewer"].on_page_load = function (wrapper) {
	wrapper.classList.add("ampower-form-viewer-page");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "",
		single_column: true,
	});

	page.main.html('<div id="ampower-form-viewer"></div>');
	const target = wrapper.querySelector("#ampower-form-viewer");

	if (frappe.ui.AmpowerFormViewer) {
		wrapper.form_viewer = new frappe.ui.AmpowerFormViewer({
			wrapper: target,
			page,
			...get_viewer_context_from_route(),
		});
		if (!wrapper.form_viewer_route_handler) {
			wrapper.form_viewer_route_handler = () => sync_form_viewer_route(wrapper);
			frappe.router.on("change", wrapper.form_viewer_route_handler);
		}
		return;
	}

	frappe.msgprint({
		title: __("Form Viewer Error"),
		message: __("Failed to load the form viewer bundle. Please refresh or contact your administrator."),
		indicator: "red",
	});
};

frappe.pages["form_viewer"].on_page_show = function (wrapper) {
	sync_form_viewer_route(wrapper);
};
