import { api, type SongDetail, type SongPatch } from '#lib/api/client.js';
import type { DraftArtist } from '#lib/features/edit/artist-list-editor.svelte';
import type { NewCover } from '#lib/features/edit/cover-editor.svelte';
import type { DraftCredit } from '#lib/features/edit/credits-editor.svelte';
import { DATE_HINT, PatchBuilder, releaseFields } from '#lib/features/edit/patch.js';
import { apiError } from '#lib/utils/api-error.js';
import { isInvalidDate, writePartialDate } from '#lib/utils/partial-date.js';

/** The song as the page being edited holds it: its fields, its artists, its credits, its genre and its tags. */
export class SongDraft {
	baseName = $state('');
	variant = $state('');
	releaseDate = $state(''); // 2012, 2012-10 or 2012-10-22; '' is no date
	description = $state('');
	genre = $state(''); // the name of a genre; '' is none
	cover = $state<NewCover | null>(null);
	tags = $state<string[]>([]);
	artists = $state<DraftArtist[]>([]);
	featured = $state<DraftArtist[]>([]);
	credits = $state<DraftCredit[]>([]);
	reset = $state({
		title: false,
		variant: false,
		date: false,
		cover: false,
		description: false,
		genre: false
	});

	constructor(private readonly song: SongDetail) {
		this.baseName = song.base_name;
		this.variant = song.variant ?? '';
		this.releaseDate = writePartialDate(song.release_date, song.release_date_precision);
		this.description = song.description ?? '';
		this.genre = song.genre ?? '';
		this.tags = [...song.tags];
		this.artists = song.artists.map(({ id, base_name }) => ({ id, base_name }));
		this.featured = song.featured.map(({ id, base_name }) => ({ id, base_name }));
		this.credits = this.shownCredits;
	}

	private get shownCredits(): DraftCredit[] {
		return this.song.credits.flatMap((group) =>
			group.artists.map((artist) => ({
				role: group.role,
				artist: { id: artist.id, base_name: artist.base_name }
			}))
		);
	}

	edited(field: string) {
		return this.song.edited.includes(field);
	}

	get dateInvalid() {
		return isInvalidDate(this.releaseDate);
	}

	/** The fields that differ from the song, and those to put back to Genius (`genre_id` is added by `save`). */
	patch(): SongPatch | null {
		const patch = new PatchBuilder<SongPatch>();
		releaseFields(patch, this, this.song);
		// A genre goes by its id, which only `save` knows; here it can only be put back.
		return patch.set(this.reset.genre, false, { genre_id: null }).build();
	}

	/** Sends what changed; the error to show, or null when everything was saved. */
	async save(): Promise<string | null> {
		if (this.dateInvalid) return `The date is not valid: ${DATE_HINT}`;
		const path = { song_id: this.song.id };
		const patch = this.patch() ?? {};
		// A genre that is picked by name: the dictionary gives its id, and makes the genre when it is new.
		if (!this.reset.genre && this.genre.trim() !== (this.song.genre ?? '')) {
			if (this.genre.trim()) {
				const { data, error } = await api.POST('/api/v1/genres', {
					body: { name: this.genre.trim() }
				});
				if (error || !data) return apiError(error);
				patch.genre_id = data.id;
			} else patch.genre_id = null;
		}
		if (Object.keys(patch).length) {
			const { error } = await api.PATCH('/api/v1/songs/{song_id}', {
				params: { path },
				body: patch
			});
			if (error) return apiError(error);
		}
		const ids = (list: DraftArtist[]) => list.map((a) => a.id).join();
		const was = {
			artists: this.song.artists.map((a) => a.id).join(),
			featured: this.song.featured.map((a) => a.id).join()
		};
		if (ids(this.artists) !== was.artists || ids(this.featured) !== was.featured) {
			const { error } = await api.PUT('/api/v1/songs/{song_id}/artists', {
				params: { path },
				body: { artists: this.artists.map((a) => a.id), featured: this.featured.map((a) => a.id) }
			});
			if (error) return apiError(error);
		}
		const key = (list: DraftCredit[]) =>
			list
				.map((c) => `${c.role}|${c.artist.id}`)
				.toSorted()
				.join();
		if (key(this.credits) !== key(this.shownCredits)) {
			const { error } = await api.PUT('/api/v1/songs/{song_id}/credits', {
				params: { path },
				body: this.credits.map((c) => ({ role: c.role, artist_id: c.artist.id }))
			});
			if (error) return apiError(error);
		}
		if (this.tags.toSorted().join() !== this.song.tags.toSorted().join()) {
			const { error } = await api.PUT('/api/v1/songs/{song_id}/tags', {
				params: { path },
				body: this.tags
			});
			if (error) return apiError(error);
		}
		return null;
	}
}
