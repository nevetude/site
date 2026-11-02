import { describe, expect, it } from 'vitest';
import type { ArtistAlbum } from '#lib/api/client.js';
import { findSeries } from '#lib/utils/find-series.js';

const album = (
	id: number,
	base_name: string,
	variant: string | null = null,
	release_date = '2015-01-01'
) => ({ id, base_name, variant, release_date }) as ArtistAlbum;

describe('findSeries', () => {
	it('joins the parts of a series, also the spellings of its name, and names it by the shared stem', () => {
		const found = findSeries([
			album(1, 'KILL YOURSELF Part II: The Black Suede Saga', null, '2014-08-06'),
			album(2, 'KILL YOURSELF Part I: The $uicide Saga', null, '2014-07-16'),
			album(3, 'KILL YOUR$ELF $agas: I - V'),
			album(4, 'Grey Sheep'),
			album(5, 'Grey Sheep II'),
			album(6, 'Taxi'),
			album(7, 'Gray/Grey')
		]);

		expect(found.map((s) => [s.name, s.albums.map((a) => a.id)])).toEqual([
			['KILL YOURSELF', [2, 1, 3]],
			['Grey Sheep', [4, 5]]
		]);
	});

	it('does not take a clean version of one album for a series', () => {
		expect(findSeries([album(1, 'Grey Sheep'), album(2, 'Grey Sheep', 'Clean Version')])).toEqual(
			[]
		);
	});

	it('takes a one-word start only when a title is that word alone and another one numbers it', () => {
		const found = findSeries([
			album(1, 'Taxi'),
			album(2, 'Taxi II'),
			album(3, 'Taxi Driver'),
			album(4, 'Razor'),
			album(5, 'Razor 2'),
			album(6, 'The Local Man'),
			album(7, 'The King Of Phonk')
		]);
		// "Taxi Driver" only begins with the same word; "The" is shared by two titles and numbers nothing.
		expect(found.map((s) => [s.name, s.albums.map((a) => a.id)])).toEqual([
			['Taxi', [1, 2]],
			['Razor', [4, 5]]
		]);
	});

	it('finds the series of Xavier Wulf by the start of the titles, and leaves alone what only begins alike', () => {
		const found = findSeries([
			album(1, 'Greatest Hits, Pt. 1', null, '2018-05-12'),
			album(2, 'Greatest Hits, Pt. 2', null, '2018-05-13'),
			album(3, 'Tundra Boy Season 2', null, '2016-11-26'),
			album(4, 'Tundra Boy Season One', null, '2015-03-22'),
			album(5, 'Blood Shore Season 3', null, '2022-10-18'),
			album(6, 'Blood Shore Season 1', null, '2014-06-12'),
			album(7, 'Blood Shore Season 2', null, '2014-10-30'),
			album(8, 'Shut Up Listen', null, '2013-11-02'),
			album(9, 'Shut Up Be Quiet', 'Damare Shizukani', '2013-03-01'),
			album(10, 'The King Of Phonk'),
			album(11, 'The Local Man')
		]);

		// The name has no comma left from "Greatest Hits, Pt. 1".
		expect(found.map((s) => [s.name, s.albums.map((a) => a.id)])).toEqual([
			['Greatest Hits', [1, 2]],
			['Tundra Boy', [4, 3]],
			['Blood Shore', [6, 7, 5]]
		]);
	});

	it('takes a number written as a word, and a season, as the numbering of a title', () => {
		expect(
			findSeries([album(1, 'Night Shift Chapter One'), album(2, 'Night Shift Chapter Two')])
		).toHaveLength(1);
		expect(findSeries([album(1, 'Dark Room'), album(2, 'Dark Side')])).toEqual([]);
		// The shared start is only "Saga Part": the word that numbers goes out of the name.
		expect(
			findSeries([album(1, 'Saga Part I: One'), album(2, 'Saga Part II: Two')]).map((s) => s.name)
		).toEqual(['Saga']);
	});
});
