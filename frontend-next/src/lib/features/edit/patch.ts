import type { AlbumPatch } from '#lib/api/client.js';
import type { NewCover } from '#lib/features/edit/cover-editor.svelte';
import { parsePartialDate, writePartialDate, type Precision } from '#lib/utils/partial-date.js';

/** What an error about a date ends with. */
export const DATE_HINT = 'write 2012, 2012-10 or 2012-10-22.';

/**
 * The patch of an album, a song or an artist, put together from the settings of the page. The keys of `values` are
 * also the names that go in `reset`, so a setting that is made of several fields (a date, a cover) is told once.
 */
export class PatchBuilder<P extends { reset?: string[] }> {
	private readonly values: Record<string, unknown> = {};
	private readonly reset: string[] = [];

	/** `reset`: the fields go back to Genius; else they are sent when the setting was `changed`. */
	set(reset: boolean, changed: boolean, values: Omit<P, 'reset'>): this {
		if (reset) this.reset.push(...Object.keys(values));
		else if (changed) Object.assign(this.values, values);
		return this;
	}

	/** The patch, or null when there is nothing to send. */
	build(): P | null {
		const patch = this.reset.length ? { ...this.values, reset: this.reset } : this.values;
		return Object.keys(patch).length ? (patch as P) : null;
	}
}

type ReleasePatch = Pick<
	AlbumPatch,
	| 'base_name'
	| 'variant'
	| 'description'
	| 'release_date'
	| 'release_date_precision'
	| 'cover_url'
	| 'cover_thumbnail_url'
	| 'cover_primary_color'
	| 'cover_secondary_color'
> & { reset?: string[] };

/** What the draft of an album and the draft of a song both hold. */
export type ReleaseDraft = {
	baseName: string;
	variant: string;
	releaseDate: string;
	description: string;
	cover: NewCover | null;
	reset: { title: boolean; variant: boolean; date: boolean; cover: boolean; description: boolean };
};
type ReleaseSaved = {
	base_name: string;
	variant: string | null;
	release_date: string | null;
	release_date_precision: Precision | null;
	description: string | null;
};

/** The title, the subtitle, the date, the cover and the description: the same for an album and for a song. */
export function releaseFields(
	patch: PatchBuilder<ReleasePatch>,
	draft: ReleaseDraft,
	saved: ReleaseSaved
) {
	const date = parsePartialDate(draft.releaseDate);
	const { cover } = draft;
	patch
		.set(draft.reset.title, draft.baseName !== saved.base_name, { base_name: draft.baseName })
		.set(draft.reset.variant, draft.variant.trim() !== (saved.variant ?? ''), {
			variant: draft.variant.trim() || null
		})
		.set(draft.reset.description, draft.description !== (saved.description ?? ''), {
			description: draft.description.trim() || null
		})
		.set(
			draft.reset.date,
			draft.releaseDate !== writePartialDate(saved.release_date, saved.release_date_precision),
			{ release_date: date?.date ?? null, release_date_precision: date?.precision ?? null }
		)
		// The values are read only when a cover was chosen; a reset needs just the names of the fields.
		.set(draft.reset.cover, cover !== null, {
			cover_url: cover?.url ?? null,
			cover_thumbnail_url: cover?.thumbnail ?? null,
			cover_primary_color: cover?.primary ?? null,
			cover_secondary_color: cover?.secondary ?? null
		});
}
