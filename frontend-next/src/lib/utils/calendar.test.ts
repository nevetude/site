import { describe, expect, it } from 'vitest';
import { daysIn, isoDay, monthWeeks, shiftMonth } from './calendar.js';

describe('monthWeeks', () => {
	it('starts on Monday and fills the first week with the days of the month before', () => {
		const weeks = monthWeeks(2026, 10); // 1 October 2026 is a Thursday
		expect(weeks[0].map((d) => d.iso)).toEqual([
			'2026-09-28',
			'2026-09-29',
			'2026-09-30',
			'2026-10-01',
			'2026-10-02',
			'2026-10-03',
			'2026-10-04'
		]);
		expect(weeks[0].map((d) => d.inMonth)).toEqual([false, false, false, true, true, true, true]);
	});

	it('shows only the weeks that the month needs', () => {
		expect(monthWeeks(2027, 2)).toHaveLength(4); // 28 days from a Monday
		expect(monthWeeks(2026, 2)).toHaveLength(5); // from a Sunday: the 1st stands alone in the first week
		expect(monthWeeks(2026, 3).every((week) => week.length === 7)).toBe(true);
	});

	it('ends with the last day of the month', () => {
		const last = monthWeeks(2026, 10).at(-1)!;
		expect(last.some((d) => d.iso === '2026-10-31')).toBe(true);
	});
});

describe('shiftMonth', () => {
	it('goes over the edge of the year', () => {
		expect(shiftMonth(2026, 12, 1)).toEqual({ year: 2027, month: 1 });
		expect(shiftMonth(2026, 1, -1)).toEqual({ year: 2025, month: 12 });
	});
});

it('knows the length of a month and writes a day', () => {
	expect(daysIn(2024, 2)).toBe(29);
	expect(isoDay(2026, 3, 5)).toBe('2026-03-05');
});
