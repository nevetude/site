import { describe, expect, it } from 'vitest';
import type { SongDetail } from '#lib/api/client.js';
import { SongDraft } from '#lib/features/song/song-draft.svelte.js';

const song = (patch: Partial<SongDetail> = {}) =>
	({
		id: 5,
		base_name: 'Song',
		variant: null,
		release_date: '2020-05-17',
		release_date_precision: 'day',
		description: null,
		genre: 'Rap',
		tags: ['rap', 'trap'],
		artists: [{ id: 1, base_name: 'Ann' }],
		featured: [],
		credits: [{ role: 'Producer', artists: [{ id: 2, base_name: 'Bob' }] }],
		edited: [],
		...patch
	}) as unknown as SongDetail;

describe('SongDraft', () => {
	it('has nothing to send until something is changed', () => {
		expect(new SongDraft(song()).patch()).toBeNull();
	});

	it('sends the fields that differ; the genre is sent by `save`, which knows its id', () => {
		const draft = new SongDraft(song());
		draft.baseName = 'Other';
		draft.variant = 'Remix';
		draft.releaseDate = '2021';
		draft.genre = 'Phonk';

		expect(draft.patch()).toEqual({
			base_name: 'Other',
			variant: 'Remix',
			release_date: '2021-01-01',
			release_date_precision: 'year'
		});
	});

	it('puts the genre back to Genius with reset', () => {
		const draft = new SongDraft(song({ edited: ['genre_id'] }));
		draft.reset.genre = true;

		expect(draft.patch()).toEqual({ reset: ['genre_id'] });
	});

	it('starts from the artists, the credits and the tags the page shows', () => {
		const draft = new SongDraft(song());

		expect(draft.artists).toEqual([{ id: 1, base_name: 'Ann' }]);
		expect(draft.credits).toEqual([{ role: 'Producer', artist: { id: 2, base_name: 'Bob' } }]);
		expect(draft.tags).toEqual(['rap', 'trap']);
	});
});
