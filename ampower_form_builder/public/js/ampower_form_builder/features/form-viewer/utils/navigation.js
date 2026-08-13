export const NEW_SUBMISSION_ROUTE_TOKEN = "new";

export function buildViewerRoute(templateName = "", submissionName = "") {
	const route = ["form_viewer"];
	if (templateName) route.push(templateName);
	if (submissionName) route.push(submissionName);
	return route;
}

export function buildViewerListRoute(templateName = "") {
	return buildViewerRoute(templateName);
}

export function buildViewerNewRoute(templateName = "") {
	return buildViewerRoute(templateName, NEW_SUBMISSION_ROUTE_TOKEN);
}

export function buildViewerSubmissionRoute(templateName = "", submissionName = "") {
	return buildViewerRoute(templateName, submissionName);
}
