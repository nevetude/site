import { describe, expect, it } from 'vitest';
import {
	describeChange,
	formatCount,
	formatDateTime,
	formatFullDate,
	formatPeriod,
	formatRelease
} from '#lib/utils/format.js';

describe('formatCount', () => {
	it('keeps small numbers and shortens big ones', () => {
		expect(formatCount(0)).toBe('0');
		expect(formatCount(999)).toBe('999');
		expect(formatCount(1000)).toBe('1K');
		expect(formatCount(1234)).toBe('1.2K');
		expect(formatCount(15_400)).toBe('15K');
		expect(formatCount(2_500_000)).toBe('2.5M');
	});
});

describe('formatRelease', () => {
	it('shows as much of the date as is really known', () => {
		expect(formatRelease('2007-01-01', 'year')).toBe('2007');
		expect(formatRelease('2007-05-01', 'month')).toBe('2007-05');
		expect(formatRelease('2007-05-17', 'day')).toBe('2007-05-17');
		expect(formatRelease(null, null)).toBeNull();
	});
});

describe('formatFullDate', () => {
	it('gives the whole date as far as it is known', () => {
		expect(formatFullDate('2026-10-05', 'day')).toBe('5 Oct 2026');
		expect(formatFullDate('2007-05-01', 'month')).toBe('May 2007');
		expect(formatFullDate('2007-01-01', 'year')).toBe('2007');
		expect(formatFullDate(null, null)).toBeNull();
	});
});

describe('describeChange', () => {
	it('writes old and new on one line and cuts long values', () => {
		expect(describeChange('followers_count', [289, 300])).toBe('followers_count: 289 → 300');
		expect(describeChange('description', [null, 'x'.repeat(100)])).toBe(
			`description: null → ${'x'.repeat(60)}…`
		);
		expect(describeChange('aliases_added', [[], ['AFX']])).toBe('aliases_added: [] → ["AFX"]');
	});
});

describe('formatDateTime', () => {
	it('writes the day like formatFullDate and the time to the minute', () => {
		expect(formatDateTime('2026-10-17T12:00:00Z')).toMatch(/^1[78] Oct 2026, \d\d:\d\d$/);
	});
});

describe('formatPeriod', () => {
	const period = (starts_on: string | null, ends_on: string | null, has_left = false) => ({
		starts_on,
		starts_precision: starts_on ? ('year' as const) : null,
		ends_on,
		ends_precision: ends_on ? ('year' as const) : null,
		has_left
	});

	it('writes the time in a group as years, with the unknown ends as "?" and "present"', () => {
		expect(formatPeriod(period('2012-01-01', '2014-01-01'))).toBe('2012–2014');
		expect(formatPeriod(period('2012-01-01', null))).toBe('2012–present');
		expect(formatPeriod(period('2013-01-01', null, true))).toBe('2013–?');
		expect(formatPeriod(period(null, null))).toBeNull();
		expect(formatPeriod(period(null, null, true))).toBe('?–?');
	});
});
