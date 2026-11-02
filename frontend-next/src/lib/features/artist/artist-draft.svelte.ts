import {
	api,
	type AlbumPatch,
	type ArtistAlbum,
	type ArtistDetail,
	type ArtistPatch,
	type MemberIn,
	type NicknameIn,
	type NicknameScope,
	type ReleaseRef,
	type SeriesIn
} from '#lib/api/client.js';
import type { NewCover } from '#lib/features/edit/cover-editor.svelte';
import { DATE_HINT, PatchBuilder } from '#lib/features/edit/patch.js';
import { apiError } from '#lib/utils/api-error.js';
import { isInvalidDate, parsePartialDate, writePartialDate } from '#lib/utils/partial-date.js';

type DraftPeriod = { start: ReleaseRef | null };
type DraftUse = { release: ReleaseRef; spelling: string; scope: NicknameScope }; // '' is the name as it is
export type DraftNickname = {
	key: number;
	kind: 'main' | 'alter_ego';
	name: string;
	spellings: string[];
	periods: DraftPeriod[];
	uses: DraftUse[];
};
/** One end of the time of a member in the group: a release (the date follows it), or a date typed. */
export type DraftBoundary = { release: ReleaseRef | null; date: string };
/** A series of releases of the artist; its releases stand in the order of their dates. */
export type DraftSeries = { key: number; name: string; albums: ArtistAlbum[] };
const byDate = (a: ArtistAlbum, b: ArtistAlbum) =>
	(a.release_date ?? '9999').localeCompare(b.release_date ?? '9999') || a.id - b.id;

// The series stand by the date of their first release; one with no release or no date goes last.
const firstDate = (s: { albums: ArtistAlbum[] }) => s.albums[0]?.release_date ?? '9999';

export type DraftMember = {
	id: number;
	name: string;
	cover: string | null;
	start: DraftBoundary;
	end: DraftBoundary;
	hasLeft: boolean;
};

const boundaryOf = (
	release: ReleaseRef | null,
	date: string | null,
	precision: 'year' | 'month' | 'day' | null
): DraftBoundary => ({ release, date: release ? '' : writePartialDate(date, precision) });

const boundaryIn = (boundary: DraftBoundary): MemberIn['start'] => {
	if (boundary.release) {
		return boundary.release.kind === 'album'
			? { album_id: boundary.release.id }
			: { song_id: boundary.release.id };
	}
	const date = parsePartialDate(boundary.date);
	return date ? { date: date.date, precision: date.precision } : null;
};

/** The artist as the page being edited holds it: the fields, the names and the members of a group. */
export class ArtistDraft {
	artistType = $state(''); // '' is not known
	description = $state('');
	realName = $state('');
	disambiguator = $state('');
	cover = $state<NewCover | null>(null);
	// The main names and the alter egos are two lists, so that each name can be bound to the card that edits it.
	mains = $state<DraftNickname[]>([]);
	egos = $state<DraftNickname[]>([]);
	members = $state<DraftMember[]>([]);
	reset = $state({
		type: false,
		description: false,
		realName: false,
		disambiguator: false,
		cover: false
	});
	/** The kind of release an album was dragged to on the page (by the id of the album); an album put back is not here. */
	albumTypes = $state<Record<number, string>>({});

	/** The aliases of Genius that are left: one taken away with the cross is gone from the page for good. */
	aliases = $state<string[]>([]);
	series = $state<DraftSeries[]>([]);
	private nextSeries = 0;

	/** How the names and the members were when the page was opened, to see whether they were changed. */
	private readonly original: {
		nicknames: string;
		members: string;
		series: string;
		aliases: string;
	};

	constructor(private readonly artist: ArtistDetail) {
		this.artistType = artist.artist_type ?? '';
		this.description = artist.description ?? '';
		this.realName = artist.real_name ?? '';
		this.disambiguator = artist.disambiguator ?? '';
		const names = artist.nicknames.map((n, key) => ({
			key,
			kind: n.kind,
			name: n.name,
			spellings: [...n.spellings],
			periods: n.periods.map((p) => ({ start: p.start })),
			uses: n.uses.map((u) => ({ release: u.release, spelling: u.spelling ?? '', scope: u.scope }))
		}));
		this.mains = names.filter((n) => n.kind === 'main');
		this.egos = names.filter((n) => n.kind === 'alter_ego');
		// The name the page has is already the first of the main names, to be changed or kept; it is saved only when changed.
		if (!this.mains.length) {
			this.mains = [
				{
					key: names.length,
					kind: 'main',
					name: artist.base_name,
					spellings: [],
					periods: [{ start: null }],
					uses: []
				}
			];
		}
		this.members = artist.members.map((m) => ({
			id: m.artist.id,
			name: m.artist.base_name,
			cover: m.artist.cover_url,
			start: boundaryOf(m.start, m.starts_on, m.starts_precision),
			end: boundaryOf(m.end, m.ends_on, m.ends_precision),
			hasLeft: m.has_left
		}));
		this.aliases = [...artist.aliases];
		this.series = artist.series.map((s) => ({
			key: this.nextSeries++,
			name: s.name,
			albums: [...s.albums]
		}));
		const saved = JSON.stringify(this.seriesIn());
		this.keepSpare();
		this.original = {
			nicknames: this.nicknamesBody,
			members: this.membersBody,
			series: saved,
			aliases: JSON.stringify(this.aliases)
		};
	}

	/** The page always ends with a series with no releases yet: the fields to start the next one. */
	private keepSpare() {
		if (!this.series.some((s) => !s.albums.length)) {
			this.series.push({ key: this.nextSeries++, name: '', albums: [] });
		}
	}

	/** Puts the series found by `findSeries` before the spare one; one that is already there by name is not doubled. */
	addFound(found: { name: string; albums: ArtistAlbum[] }[]) {
		this.series = this.series.filter((s) => s.albums.length || s.name.trim());
		for (const one of found.toSorted((a, b) => firstDate(a).localeCompare(firstDate(b)))) {
			if (this.series.some((s) => s.name.trim() === one.name)) continue;
			this.series.push({ key: this.nextSeries++, name: one.name, albums: [...one.albums] });
		}
		this.keepSpare();
	}

	removeSeries(key: number) {
		this.series = this.series.filter((s) => s.key !== key);
		this.keepSpare();
	}

	/** False when the release is in the series already. */
	addToSeries(key: number, album: ArtistAlbum) {
		const one = this.series.find((s) => s.key === key);
		if (!one || one.albums.some((a) => a.id === album.id)) return false;
		one.albums = [...one.albums, album].sort(byDate);
		this.keepSpare();
		return true;
	}

	removeFromSeries(key: number, albumId: number) {
		const one = this.series.find((s) => s.key === key);
		if (one) one.albums = one.albums.filter((a) => a.id !== albumId);
	}

	seriesIn(): SeriesIn[] {
		return this.series
			.filter((s) => s.name.trim() || s.albums.length) // the name is optional; a series with neither is the spare
			.toSorted((a, b) => firstDate(a).localeCompare(firstDate(b)))
			.map((s) => ({ name: s.name.trim(), album_ids: s.albums.map((a) => a.id) }));
	}

	edited(field: string) {
		return this.artist.edited.includes(field);
	}

	private get nicknamesBody() {
		return JSON.stringify(this.nicknamesIn());
	}

	private get membersBody() {
		return JSON.stringify(this.membersIn());
	}

	nicknamesIn(): NicknameIn[] {
		return [...this.mains, ...this.egos]
			.filter((n) => n.name.trim())
			.map((n) => ({
				kind: n.kind,
				name: n.name.trim(),
				spellings: n.spellings,
				periods:
					n.kind === 'main'
						? n.periods.map((p) =>
								p.start?.kind === 'album'
									? { start_album_id: p.start.id }
									: p.start
										? { start_song_id: p.start.id }
										: {}
							)
						: [],
				uses: n.uses.map((u) => ({
					...(u.release.kind === 'album' ? { album_id: u.release.id } : { song_id: u.release.id }),
					spelling: u.spelling || null,
					scope: u.scope
				}))
			}));
	}

	membersIn(): MemberIn[] {
		return this.members.map((m) => ({
			member_id: m.id,
			start: boundaryIn(m.start),
			end: boundaryIn(m.end),
			has_left: m.hasLeft
		}));
	}

	/** A date typed in a field of a member that is not one: the member and the end, for the message. */
	get invalidDate() {
		for (const m of this.members) {
			for (const b of [m.start, m.end]) {
				if (!b.release && isInvalidDate(b.date)) return m.name;
			}
		}
		return null;
	}

	patch(): ArtistPatch | null {
		const a = this.artist;
		return new PatchBuilder<ArtistPatch>()
			.set(this.reset.type, this.artistType !== (a.artist_type ?? ''), {
				artist_type: (this.artistType || null) as ArtistPatch['artist_type']
			})
			.set(this.reset.description, this.description !== (a.description ?? ''), {
				description: this.description.trim() || null
			})
			.set(this.reset.disambiguator, this.disambiguator.trim() !== (a.disambiguator ?? ''), {
				disambiguator: this.disambiguator.trim() || null
			})
			.set(this.reset.realName, this.realName.trim() !== (a.real_name ?? ''), {
				real_name: this.realName.trim() || null
			})
			.set(this.reset.cover, this.cover !== null, { cover_url: this.cover?.url ?? null })
			.build();
	}

	/** Sends what changed; the error to show, or null when everything was saved. */
	async save(): Promise<string | null> {
		const bad = this.invalidDate;
		if (bad) return `A date of ${bad} is not valid: ${DATE_HINT}`;
		const path = { artist_id: this.artist.id };
		const patch = this.patch();
		if (patch) {
			const { error } = await api.PATCH('/api/v1/artists/{artist_id}', {
				params: { path },
				body: patch
			});
			if (error) return apiError(error);
		}
		if (this.nicknamesBody !== this.original.nicknames) {
			const { error } = await api.PUT('/api/v1/artists/{artist_id}/nicknames', {
				params: { path },
				body: this.nicknamesIn()
			});
			if (error) return apiError(error);
		}
		if (this.membersBody !== this.original.members) {
			const { error } = await api.PUT('/api/v1/artists/{group_id}/members', {
				params: { path: { group_id: this.artist.id } },
				body: this.membersIn()
			});
			if (error) return apiError(error);
		}
		if (JSON.stringify(this.aliases) !== this.original.aliases) {
			const { error } = await api.PUT('/api/v1/artists/{artist_id}/aliases', {
				params: { path },
				body: this.aliases
			});
			if (error) return apiError(error);
		}
		if (JSON.stringify(this.seriesIn()) !== this.original.series) {
			const { error } = await api.PUT('/api/v1/artists/{artist_id}/series', {
				params: { path },
				body: this.seriesIn()
			});
			if (error) return apiError(error);
		}
		for (const [id, album_type] of Object.entries(this.albumTypes)) {
			const { error } = await api.PATCH('/api/v1/albums/{album_id}', {
				params: { path: { album_id: Number(id) } },
				body: { album_type: album_type as AlbumPatch['album_type'] }
			});
			if (error) return apiError(error);
		}
		return null;
	}
}
