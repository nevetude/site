import { describe, expect, it } from 'vitest';
import type { AlbumDetail, AlbumTrack } from '#lib/api/client.js';
import { AlbumDraft } from '#lib/features/album/album-draft.svelte.js';

const album = (patch: Partial<AlbumDetail> = {}) =>
	({
		id: 7,
		base_name: 'Title',
		variant: 'Deluxe',
		album_type: 'album',
		is_released: true,
		release_date: '2012-10-22',
		release_date_precision: 'day',
		description: 'Text',
		edited: [],
		credits: [],
		artists: [],
		...patch
	}) as unknown as AlbumDetail;
const track = (id: number, song_id: number) =>
	({ id, song_id, base_name: `Song ${song_id}`, variant: null, disc_number: 1 }) as AlbumTrack;

describe('AlbumDraft', () => {
	it('has nothing to send until something is changed', () => {
		expect(new AlbumDraft(album(), []).patch()).toBeNull();
	});

	it('sends only the fields that differ, and a date with how much of it is known', () => {
		const draft = new AlbumDraft(album(), []);
		draft.baseName = 'New title';
		draft.variant = '  ';
		draft.status = 'unreleased';
		draft.releaseDate = '2013-05';

		expect(draft.patch()).toEqual({
			base_name: 'New title',
			variant: null,
			is_released: false,
			release_date: '2013-05-01',
			release_date_precision: 'month'
		});
	});

	it('takes a date away with null, and refuses what is not a date', () => {
		const draft = new AlbumDraft(album(), []);
		draft.releaseDate = '';
		expect(draft.patch()).toEqual({ release_date: null, release_date_precision: null });

		draft.releaseDate = '2012-02-31';
		expect(draft.dateInvalid).toBe(true);
	});

	it('puts a field back to Genius with reset, and does not send its value', () => {
		const draft = new AlbumDraft(album({ edited: ['base_name', 'release_date'] }), []);
		draft.baseName = 'Typed after';
		draft.reset.title = true;
		draft.reset.date = true;

		expect(draft.patch()).toEqual({
			reset: ['base_name', 'release_date', 'release_date_precision']
		});
	});

	it('changes the cover as four fields', () => {
		const draft = new AlbumDraft(album(), []);
		draft.cover = {
			url: 'https://x/c.jpg',
			thumbnail: 'https://x/t.jpg',
			primary: null,
			secondary: null
		};

		expect(draft.patch()).toEqual({
			cover_url: 'https://x/c.jpg',
			cover_thumbnail_url: 'https://x/t.jpg',
			cover_primary_color: null,
			cover_secondary_color: null
		});
	});

	it('knows the list of tracks was changed only by the songs and their order', () => {
		const draft = new AlbumDraft(album(), [track(1, 10), track(2, 20)]);
		expect(draft.tracks.map((t) => t.song_id)).toEqual([10, 20]);
		draft.tracks = draft.tracks.toReversed();
		expect(draft.tracks.map((t) => t.song_id)).toEqual([20, 10]);
	});
});
