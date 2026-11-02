import { api, type AlbumDetail, type AlbumPatch, type AlbumTrack } from '#lib/api/client.js';
import type { DraftArtist } from '#lib/features/edit/artist-list-editor.svelte';
import type { DraftCredit } from '#lib/features/edit/credits-editor.svelte';
import type { DraftTrack } from '#lib/features/album/tracklist-editor.svelte';
import type { NewCover } from '#lib/features/edit/cover-editor.svelte';
import { DATE_HINT, PatchBuilder, releaseFields } from '#lib/features/edit/patch.js';
import { apiError } from '#lib/utils/api-error.js';
import { isInvalidDate, writePartialDate } from '#lib/utils/partial-date.js';

/** The album as the page being edited holds it: every field and list the user can change, and what to send to save. */
export class AlbumDraft {
	baseName = $state('');
	variant = $state('');
	albumType = $state(''); // '' is no type
	status = $state<'released' | 'unreleased' | ''>(''); // '' is not known
	releaseDate = $state(''); // 2012, 2012-10 or 2012-10-22; '' is no date
	description = $state('');
	cover = $state<NewCover | null>(null); // set when another cover is chosen
	tracks = $state<DraftTrack[]>([]);
	credits = $state<DraftCredit[]>([]);
	artists = $state<DraftArtist[]>([]); // the artists of the album, in order
	// The fields that were set by hand and are to go back to Genius when saved.
	reset = $state({
		title: false,
		variant: false,
		type: false,
		status: false,
		date: false,
		cover: false,
		description: false
	});

	constructor(
		private readonly album: AlbumDetail,
		tracks: AlbumTrack[]
	) {
		this.baseName = album.base_name;
		this.variant = album.variant ?? '';
		this.albumType = album.album_type ?? '';
		this.status = album.is_released === null ? '' : album.is_released ? 'released' : 'unreleased';
		this.releaseDate = writePartialDate(album.release_date, album.release_date_precision);
		this.description = album.description ?? '';
		this.tracks = tracks.map((t) => ({
			key: t.id,
			song_id: t.song_id,
			name: t.base_name,
			variant: t.variant,
			disc_number: t.disc_number
		}));
		this.credits = this.shownCredits;
		this.artists = album.artists.map(({ id, base_name }) => ({ id, base_name }));
		this.original = tracks.map((t) => `${t.song_id}/${t.disc_number}`).join();
	}

	/** The credits of the album itself (a role and an artist); the ones summed up from the songs are not its own. */
	private get shownCredits(): DraftCredit[] {
		return this.album.credits.flatMap((group) =>
			group.artists
				.filter((one) => one.tracks === null)
				.map((one) => ({
					role: group.role,
					artist: { id: one.artist.id, base_name: one.artist.base_name }
				}))
		);
	}

	/** The tracks as they were when the page was opened, to see whether the list was changed. */
	private readonly original: string;

	edited(field: string) {
		return this.album.edited.includes(field);
	}

	get dateInvalid() {
		return isInvalidDate(this.releaseDate);
	}

	private get tracksChanged() {
		return this.tracks.map((t) => `${t.song_id}/${t.disc_number}`).join() !== this.original;
	}

	private get creditsChanged() {
		const key = (list: DraftCredit[]) =>
			list
				.map((c) => `${c.role}|${c.artist.id}`)
				.toSorted()
				.join();
		return key(this.credits) !== key(this.shownCredits);
	}

	/** The fields that differ from the album, and those to put back to Genius; null when there are none. */
	patch(): AlbumPatch | null {
		const a = this.album;
		const patch = new PatchBuilder<AlbumPatch>();
		releaseFields(patch, this, a);
		const known = a.is_released === null ? '' : a.is_released ? 'released' : 'unreleased';
		return patch
			.set(this.reset.type, this.albumType !== (a.album_type ?? ''), {
				album_type: (this.albumType || null) as AlbumPatch['album_type']
			})
			.set(this.reset.status, this.status !== known, {
				is_released: this.status === '' ? null : this.status === 'released'
			})
			.build();
	}

	/** Sends what changed; the error to show, or null when everything was saved. */
	async save(): Promise<string | null> {
		if (this.dateInvalid) return `The date is not valid: ${DATE_HINT}`;
		const path = { album_id: this.album.id };
		const patch = this.patch();
		if (patch) {
			const { error } = await api.PATCH('/api/v1/albums/{album_id}', {
				params: { path },
				body: patch
			});
			if (error) return apiError(error);
		}
		if (this.tracksChanged) {
			const { error } = await api.PUT('/api/v1/albums/{album_id}/tracks', {
				params: { path },
				body: this.tracks.map(({ song_id, disc_number }) => ({ song_id, disc_number }))
			});
			if (error) return apiError(error);
		}
		const ids = (list: { id: number }[]) => list.map((a) => a.id).join();
		if (ids(this.artists) !== ids(this.album.artists)) {
			const { error } = await api.PUT('/api/v1/albums/{album_id}/artists', {
				params: { path },
				body: this.artists.map((a) => a.id)
			});
			if (error) return apiError(error);
		}
		if (this.creditsChanged) {
			const { error } = await api.PUT('/api/v1/albums/{album_id}/credits', {
				params: { path },
				body: this.credits.map((c) => ({ role: c.role, artist_id: c.artist.id }))
			});
			if (error) return apiError(error);
		}
		return null;
	}
}
