import { describe, expect, it } from 'vitest';
import type { NicknameOut } from '#lib/api/client.js';
import { nameTimeline } from '#lib/utils/nicknames.js';

const release = (release_date: string) => ({
	kind: 'album' as const,
	id: 1,
	name: 'x',
	variant: null,
	release_date,
	release_date_precision: 'day' as const
});
const main = (name: string, ...starts: (string | null)[]): NicknameOut => ({
	id: 1,
	kind: 'main',
	name,
	spellings: [],
	periods: starts.map((s, i) => ({ id: i, start: s ? release(s) : null })),
	uses: []
});

describe('nameTimeline', () => {
	it('puts the names in the order of their dates, and a name that came back twice', () => {
		const names = [
			main('Snoop Dogg', '1996-11-12', '2015-05-12'),
			main('Snoop Lion', '2013-04-23'),
			main('Snoop Doggy Dogg', null),
			{ ...main('Snoopzilla', null), kind: 'alter_ego' as const }
		];

		expect(nameTimeline(names).map((n) => [n.name, n.from])).toEqual([
			['Snoop Doggy Dogg', null],
			['Snoop Dogg', '1996'],
			['Snoop Lion', '2013'],
			['Snoop Dogg', '2015']
		]);
	});
});
