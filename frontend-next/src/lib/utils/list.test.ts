import { describe, expect, it } from 'vitest';
import { moved } from '#lib/utils/list.js';

describe('moved', () => {
	it('puts an item at another place and shifts the ones between', () => {
		expect(moved(['a', 'b', 'c', 'd'], 0, 2)).toEqual(['b', 'c', 'a', 'd']);
		expect(moved(['a', 'b', 'c', 'd'], 3, 1)).toEqual(['a', 'd', 'b', 'c']);
	});

	it('leaves the list as it is when the place is outside of it', () => {
		const list = ['a', 'b'];
		expect(moved(list, 0, -1)).toBe(list);
		expect(moved(list, 1, 2)).toBe(list);
		expect(moved(list, 1, 1)).toBe(list);
	});
});
