import { describe, expect, it } from 'vitest';
import { isInvalidDate, parsePartialDate, writePartialDate } from '#lib/utils/partial-date.js';

describe('partial dates', () => {
	it('reads a year, a month and a day, and pads the rest with 1', () => {
		expect(parsePartialDate('2012')).toEqual({ date: '2012-01-01', precision: 'year' });
		expect(parsePartialDate('2012-05')).toEqual({ date: '2012-05-01', precision: 'month' });
		expect(parsePartialDate(' 2012-05-17 ')).toEqual({ date: '2012-05-17', precision: 'day' });
	});

	it('refuses what is not a date', () => {
		for (const text of ['', 'abc', '12', '2012-13', '2012-02-31', '2012-5']) {
			expect(parsePartialDate(text)).toBeNull();
		}
	});

	it('lets an empty field be, and blames only what was typed wrong', () => {
		expect(isInvalidDate('')).toBe(false);
		expect(isInvalidDate('2012-05')).toBe(false);
		expect(isInvalidDate('2012-02-31')).toBe(true);
	});

	it('writes a date as far as it is known', () => {
		expect(writePartialDate('2012-05-17', 'day')).toBe('2012-05-17');
		expect(writePartialDate('2012-05-01', 'month')).toBe('2012-05');
		expect(writePartialDate('2012-01-01', null)).toBe('2012');
		expect(writePartialDate(null, null)).toBe('');
	});
});
