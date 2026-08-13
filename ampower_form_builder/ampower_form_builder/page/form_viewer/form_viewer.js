function getViewerRouteContext(route = frappe.get_route ? frappe.get_route() : []) {
	const segments = Array.isArray(route) ? route : [];
	const urlParams = new URLSearchParams(window.location.search);
	return {
		templateName: segments[1] || urlParams.get("template") || "",
		submissionName: segments[2] || urlParams.get("submission") || "",
	};
}

function buildViewerRoute(templateName = "", submissionName = "") {
	const route = ["form_viewer"];
	if (templateName) route.push(templateName);
	if (submissionName) route.push(submissionName);
	return route;
}

function getViewerTitle(context = {}) {
	if (context.submissionName) return context.submissionName;
	if (context.templateName) return context.templateName;
	return __("Form Viewer");
}

class FormViewerPageRenderer {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = null;
		this.viewer = null;
		this.routeHandler = null;
		this.routeKey = "";
	}

	ensureMounted(context = getViewerRouteContext()) {
		if (this.viewer) return;

		this.page = frappe.ui.make_app_page({
			parent: this.wrapper,
			title: "",
			single_column: true,
		});

		this.page.main.html('<div id="ampower-form-viewer"></div>');
		const target = this.wrapper.querySelector("#ampower-form-viewer");

		if (!frappe.ui.AmpowerFormViewer) {
			frappe.msgprint({
				title: __("Form Viewer Error"),
				message: __("Failed to load the form viewer bundle. Please refresh or contact your administrator."),
				indicator: "red",
			});
			return;
		}

		this.viewer = new frappe.ui.AmpowerFormViewer({
			wrapper: target,
			page: this.page,
			...context,
		});

		if (!this.routeHandler) {
			this.routeHandler = () => this.render();
			frappe.router.on("change", this.routeHandler);
		}
	}

	render() {
		const route = frappe.get_route ? frappe.get_route() : [];
		if (route[0] !== "form_viewer") return;

		const context = getViewerRouteContext(route);
		const nextKey = `${context.templateName || ""}::${context.submissionName || ""}`;
		if (this.page?.set_title) {
			this.page.set_title(getViewerTitle(context));
		}

		if (nextKey === this.routeKey && this.viewer) {
			this.viewer.update(context);
			return;
		}

		this.routeKey = nextKey;
		this.ensureMounted(context);
		this.viewer?.update(context);
	}

	destroy() {
		if (this.routeHandler && frappe.router?.off) {
			frappe.router.off("change", this.routeHandler);
		}
		this.routeHandler = null;
		this.routeKey = "";
		if (this.viewer) {
			this.viewer.destroy?.();
		}
		this.viewer = null;
		this.page = null;
		if (this.wrapper?.innerHTML !== undefined) {
			this.wrapper.innerHTML = "";
		}
	}
}

frappe.pages["form_viewer"].on_page_load = function (wrapper) {
	wrapper.classList.add("ampower-form-viewer-page");
	wrapper.form_viewer_renderer = new FormViewerPageRenderer(wrapper);
	wrapper.form_viewer_renderer.render();
};

frappe.pages["form_viewer"].on_page_show = function (wrapper) {
	wrapper.form_viewer_renderer?.render();
};

frappe.pages["form_viewer"].on_page_unload = function (wrapper) {
	wrapper.form_viewer_renderer?.destroy();
	delete wrapper.form_viewer_renderer;
};