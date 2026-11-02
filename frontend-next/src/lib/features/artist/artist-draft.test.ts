import { describe, expect, it } from 'vitest';
import type { ArtistDetail, NicknameOut } from '#lib/api/client.js';
import { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';

const release = (kind: 'album' | 'song', id: number) => ({
	kind,
	id,
	name: 'R',
	variant: null,
	release_date: '2013-04-23',
	release_date_precision: 'day' as const
});
const artist = (nicknames: NicknameOut[] = []) =>
	({
		id: 3,
		base_name: 'Thom',
		artist_type: 'group',
		description: 'Bio',
		edited: [],
		nicknames,
		series: [],
		aliases: [],
		members: [
			{
				artist: { id: 11, base_name: 'Ann', cover_url: null },
				starts_on: '2012-01-01',
				starts_precision: 'year',
				ends_on: null,
				ends_precision: null,
				has_left: false,
				start: null,
				end: null
			}
		]
	}) as unknown as ArtistDetail;

describe('ArtistDraft', () => {
	it('has nothing to send until something is changed', () => {
		const draft = new ArtistDraft(artist());
		expect(draft.patch()).toBeNull();
		// the name of the page is the first main name already, and it stays as it is until it is changed
		expect(draft.nicknamesIn().map((n) => n.name)).toEqual(['Thom']);
	});

	it('sends the type and the description that differ', () => {
		const draft = new ArtistDraft(artist());
		draft.artistType = 'person';
		draft.description = '';

		expect(draft.patch()).toEqual({ artist_type: 'person', description: null });
	});

	it('writes the names for the API: a period starts with an album or a song or with nothing', () => {
		const draft = new ArtistDraft(artist());
		draft.mains = [
			{
				key: 1,
				kind: 'main',
				name: ' Snoop Dogg ',
				spellings: ['SNOOP DOGG'],
				periods: [{ start: null }, { start: release('album', 5) }, { start: release('song', 6) }],
				uses: [{ release: release('album', 5), spelling: 'SNOOP DOGG', scope: 'any' }]
			},
			{ key: 2, kind: 'main', name: '   ', spellings: [], periods: [], uses: [] } // empty: left out
		];
		draft.egos = [
			{
				key: 3,
				kind: 'alter_ego',
				name: 'Snoopzilla',
				spellings: [],
				periods: [{ start: release('album', 9) }], // an alter ego has no periods
				uses: [{ release: release('song', 8), spelling: '', scope: 'credit' }]
			}
		];

		expect(draft.nicknamesIn()).toEqual([
			{
				kind: 'main',
				name: 'Snoop Dogg',
				spellings: ['SNOOP DOGG'],
				periods: [{}, { start_album_id: 5 }, { start_song_id: 6 }],
				uses: [{ album_id: 5, spelling: 'SNOOP DOGG', scope: 'any' }]
			},
			{
				kind: 'alter_ego',
				name: 'Snoopzilla',
				spellings: [],
				periods: [],
				uses: [{ song_id: 8, spelling: null, scope: 'credit' }]
			}
		]);
	});

	it('writes the time of a member as a release or as a date known to the year, month or day', () => {
		const draft = new ArtistDraft(artist());
		expect(draft.membersIn()).toEqual([
			{
				member_id: 11,
				start: { date: '2012-01-01', precision: 'year' },
				end: null,
				has_left: false
			}
		]);

		draft.members[0].start = { release: release('song', 4), date: '' };
		draft.members[0].end = { release: null, date: '2014-06' };
		draft.members[0].hasLeft = true;

		expect(draft.membersIn()).toEqual([
			{
				member_id: 11,
				start: { song_id: 4 },
				end: { date: '2014-06-01', precision: 'month' },
				has_left: true
			}
		]);
	});

	it('names the member whose date is not a date', () => {
		const draft = new ArtistDraft(artist());
		expect(draft.invalidDate).toBeNull();
		draft.members[0].end = { release: null, date: 'soon' };
		expect(draft.invalidDate).toBe('Ann');
	});

	it('keeps the releases of a series in the order of their dates and adds one only once', () => {
		const draft = new ArtistDraft(artist());
		const album = (id: number, release_date: string | null) => ({ id, release_date }) as never;
		const { key } = draft.series[0];
		draft.series[0].name = ' Vol ';

		expect(draft.addToSeries(key, album(1, '2015-01-01'))).toBe(true);
		draft.addToSeries(key, album(2, null));
		draft.addToSeries(key, album(3, '2013-01-01'));

		expect(draft.addToSeries(key, album(3, '2013-01-01'))).toBe(false);
		expect(draft.seriesIn()).toEqual([{ name: 'Vol', album_ids: [3, 1, 2] }]);

		draft.addFound([
			{ name: 'Older', albums: [album(8, '2010-01-01')] },
			{ name: 'Vol', albums: [album(9, '2020-01-01')] }
		]);
		expect(draft.series.map((s) => s.name)).toEqual([' Vol ', 'Older', '']); // 'Vol' is there already
		expect(draft.seriesIn().map((s) => s.name)).toEqual(['Older', 'Vol']); // saved by the first release

		draft.series[0].name = '';
		expect(draft.seriesIn().map((s) => s.name)).toEqual(['Older', '']); // the name is optional
		expect(draft.series.at(-1)?.albums).toEqual([]); // and a spare series waits for the next one
	});
});
