export type Day = { iso: string; day: number; inMonth: boolean };

const pad = (n: number) => String(n).padStart(2, '0');

/** `2026-10-31` for a day of the month; the calendar works on UTC dates so that the time zone never moves a day. */
export const isoDay = (year: number, month: number, day: number) =>
	`${year}-${pad(month)}-${pad(day)}`;

/** The weeks (Monday first) that show a month, with the days of the neighbours that fill the first and the last week. */
export function monthWeeks(year: number, month: number): Day[][] {
	const first = new Date(Date.UTC(year, month - 1, 1));
	const lead = (first.getUTCDay() + 6) % 7; // days of the previous month before the 1st
	const weeks: Day[][] = [];
	for (let start = 1 - lead; start <= daysIn(year, month); start += 7) {
		weeks.push(
			Array.from({ length: 7 }, (_, i) => {
				const d = new Date(Date.UTC(year, month - 1, start + i));
				return {
					iso: isoDay(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()),
					day: d.getUTCDate(),
					inMonth: d.getUTCMonth() === month - 1
				};
			})
		);
	}
	return weeks;
}

export const daysIn = (year: number, month: number) =>
	new Date(Date.UTC(year, month, 0)).getUTCDate();

/** The month before or after (`step` -1 or 1). */
export function shiftMonth(year: number, month: number, step: number) {
	const d = new Date(Date.UTC(year, month - 1 + step, 1));
	return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1 };
}
