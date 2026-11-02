/** The list with the item at `from` put at `to`; the same list when `to` is not a place in it. */
export function moved<T>(list: T[], from: number, to: number): T[] {
	if (from === to || to < 0 || to >= list.length) return list;
	const next = [...list];
	next.splice(to, 0, ...next.splice(from, 1));
	return next;
}
