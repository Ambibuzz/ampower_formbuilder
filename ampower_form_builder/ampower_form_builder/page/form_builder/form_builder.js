frappe.pages["form_builder"].on_page_load = function (wrapper) {
	wrapper.classList.add("ampower-form-builder-page");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "",
		single_column: true,
	});

	page.main.html('<div id="ampower-form-builder"></div>');
	const target = wrapper.querySelector("#ampower-form-builder");

	if (frappe.ui.AmpowerFormBuilder) {
		new frappe.ui.AmpowerFormBuilder({
			wrapper: target,
			page,
		});
		return;
	}

	frappe.msgprint({
		title: "Form Builder Error",
		message: "Failed to load the form builder bundle. Please refresh or contact your administrator.",
		indicator: "red",
	});
};
