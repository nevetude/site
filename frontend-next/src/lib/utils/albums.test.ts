import { describe, expect, it } from 'vitest';
import {
	byDisc,
	CARD,
	cardHeight,
	cardSpan,
	coverList,
	coverSize,
	differs,
	isDefaultCover,
	perRow,
	popularity,
	relationTitle,
	sortRoles
} from '#lib/utils/albums.js';

describe('relationTitle', () => {
	it('words the relation from the side of this album', () => {
		expect(relationTitle({ type: 'deluxe_edition_of', inverse: false })).toBe('Deluxe edition of');
		expect(relationTitle({ type: 'deluxe_edition_of', inverse: true })).toBe('Deluxe editions');
		expect(relationTitle({ type: 'remix_version_of', inverse: true })).toBe('Remixes');
	});
});

describe('byDisc', () => {
	it('groups by disc in the order of arrival, a missing disc being the first', () => {
		const discs = byDisc([
			{ disc_number: null, n: 1 },
			{ disc_number: 2, n: 2 },
			{ disc_number: 1, n: 3 }
		]);
		expect(discs.map((d) => [d.number, d.tracks.map((t) => t.n)])).toEqual([
			[1, [1, 3]],
			[2, [2]]
		]);
	});
});

describe('differs', () => {
	it('says whether a track has other artists than the album', () => {
		expect(differs([{ id: 1 }], [{ id: 1 }])).toBe(false);
		expect(differs([{ id: 2 }], [{ id: 1 }])).toBe(true);
		expect(differs([{ id: 1 }, { id: 2 }], [{ id: 1 }])).toBe(true);
		expect(differs([], [{ id: 1 }])).toBe(true);
	});
});

describe('coverList', () => {
	const cover = (image_url: string) => ({ image_url, thumbnail_image_url: `${image_url}-t` });
	const pair = (url: string) => ({
		url,
		thumb: `${url}-t`,
		explicit: undefined,
		placeholder: false
	});

	it('puts the main cover first and adds it when Genius does not list it', () => {
		const covers = [cover('a'), cover('b'), cover('c')] as never;
		const base = { cover_thumbnail_url: 'z-t', covers };
		expect(coverList({ ...base, cover_url: 'b' })).toEqual([pair('b'), pair('a'), pair('c')]);
		expect(coverList({ ...base, cover_url: 'z' })).toEqual([
			pair('z'),
			pair('a'),
			pair('b'),
			pair('c')
		]);
		expect(coverList({ cover_url: null, cover_thumbnail_url: null, covers: [] })).toEqual([]);
	});

	it('marks the picture Genius gives an album with no cover, so that the site draws a grey box instead', () => {
		const url = 'https://assets.genius.com/images/default_cover_image.png';
		const covers = [{ image_url: url, thumbnail_image_url: url, explicit: false }] as never;
		expect(coverList({ cover_url: url, cover_thumbnail_url: url, covers })[0].placeholder).toBe(
			true
		);
		expect(isDefaultCover(url)).toBe(true);
		expect(isDefaultCover('https://images.genius.com/x.jpg')).toBe(false);
	});
});

describe('sortRoles', () => {
	it('puts producers and writers first and keeps the order of the rest', () => {
		const roles = ['Label', 'Writer', 'Mixing', 'Producer'].map((role) => ({ role })) as never;
		expect(sortRoles(roles).map((g) => g.role)).toEqual(['Producer', 'Writer', 'Label', 'Mixing']);
	});
});

describe('popularity', () => {
	it('ranks the best viewed tracks and skips the ones without a count', () => {
		const rank = popularity(
			[
				{ song_id: 1, view_count: 10 },
				{ song_id: 2, view_count: null },
				{ song_id: 3, view_count: 50 },
				{ song_id: 4, view_count: 30 }
			],
			2
		);
		expect([...rank]).toEqual([
			[3, 1],
			[4, 2]
		]);
	});
});

describe('card geometry', () => {
	it('puts two cells under a card of the rows view', () => {
		expect(perRow(1203, 'grid')).toBe(8);
		expect(perRow(1203, 'list')).toBe(4);
		expect(perRow(1050, 'list')).toBe(3); // 7 cells: the last one stays empty
		expect(perRow(100, 'list')).toBe(1);
		expect(cardSpan(100, 'list')).toBe(1); // one cell is all there is
	});

	it('makes a card of the rows view as tall as the cover of a grid card is wide', () => {
		// 1200 / 8 = a 150 wide cell; the rows view has the cover only, the grid view the text under it
		expect(cardHeight(1200, 'list')).toBe(150);
		expect(cardHeight(1200, 'grid')).toBe(150 + CARD.text);
		expect(coverSize(1200)).toBe(150 - CARD.pad); // the same cover in both views
	});
});
