function get_print_builder_context() {
	const route = frappe.get_route ? frappe.get_route() : [];
	const urlParams = new URLSearchParams(window.location.search);

	return {
		formatName: route[1] || urlParams.get("format") || "",
		templateName: urlParams.get("template") || "",
	};
}

function sync_print_builder_route(wrapper) {
	if (!wrapper.print_builder) return;
	wrapper.print_builder.update(get_print_builder_context());
}

frappe.pages["print_builder"].on_page_load = function (wrapper) {
	wrapper.classList.add("ampower-print-builder-page");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "",
		single_column: true,
	});
	page.container.addClass("full-width");

	page.main.html('<div id="ampower-print-builder"></div>');
	const target = wrapper.querySelector("#ampower-print-builder");

	if (frappe.ui.AmpowerPrintBuilder) {
		wrapper.print_builder = new frappe.ui.AmpowerPrintBuilder({
			wrapper: target,
			page,
			...get_print_builder_context(),
		});
		if (!wrapper.print_builder_route_handler) {
			wrapper.print_builder_route_handler = () => sync_print_builder_route(wrapper);
			frappe.router.on("change", wrapper.print_builder_route_handler);
		}
		return;
	}

	frappe.msgprint({
		title: __("Print Builder Error"),
		message: __("Failed to load the print builder bundle. Please refresh or contact your administrator."),
		indicator: "red",
	});
};

frappe.pages["print_builder"].on_page_show = function (wrapper) {
	sync_print_builder_route(wrapper);
};
