export type Precision = 'year' | 'month' | 'day';

/** "2012", "2012-05" or "2012-05-17" as a date and how much of it is known (the rest is 1, like Genius pads it). */
export function parsePartialDate(text: string): { date: string; precision: Precision } | null {
	const match = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(text.trim());
	if (!match) return null;
	const [, year, month = '01', day = '01'] = match;
	const [y, m, d] = [Number(year), Number(month), Number(day)];
	// A month or a day that does not exist (13, 31 February) rolls over into the next one: that is not a date.
	const check = new Date(Date.UTC(y, m - 1, d));
	if (check.getUTCFullYear() !== y || check.getUTCMonth() !== m - 1 || check.getUTCDate() !== d)
		return null;
	const date = `${year}-${month}-${day}`;
	return { date, precision: match[3] ? 'day' : match[2] ? 'month' : 'year' };
}

/** The inverse of `parsePartialDate`, as it is typed in a field; an empty field for no date. */
export function writePartialDate(date: string | null, precision: Precision | null) {
	if (!date) return '';
	return date.slice(0, precision === 'day' ? 10 : precision === 'month' ? 7 : 4);
}

/** Something typed in a date field that is not a date (an empty field is no date, and that is fine). */
export const isInvalidDate = (text: string) => text !== '' && parsePartialDate(text) === null;
