/** What an answer of the API that was not ok says, for a person (the body of a 4xx is `{ detail }`). */
export function apiError(error: unknown) {
	const detail = (error as { detail?: unknown } | undefined)?.detail;
	if (typeof detail === 'string') return detail;
	if (Array.isArray(detail)) return detail.map((one: { msg: string }) => one.msg).join('; ');
	return 'The change was not saved.';
}
