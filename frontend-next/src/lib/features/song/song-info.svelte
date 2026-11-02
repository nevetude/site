<script lang="ts">
	import type { SongDetail } from '#lib/api/client.js';
	import { languageName } from '#lib/utils/albums.js';
	import { formatCount, formatFullDate } from '#lib/utils/format.js';
	import FactRow from '#lib/components/fact-row.svelte';
	import { api } from '#lib/api/client.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import ChipsEditor from '#lib/features/edit/chips-editor.svelte';
	import PartialDateInput from '#lib/features/edit/partial-date-input.svelte';
	import ResetField from '#lib/features/edit/reset-field.svelte';
	import type { SongDraft } from '#lib/features/song/song-draft.svelte.js';

	// `draft`: the page is being edited, and the date, the genre and the tags are fields.
	let { song, draft = $bindable(null) }: { song: SongDetail; draft?: SongDraft | null } = $props();

	const genreListId = $props.id();
	let genres = $state<string[]>([]);
	async function suggestGenres() {
		const q = draft?.genre ?? '';
		genres = ((await api.GET('/api/v1/genres', { params: { query: { q } } })).data ?? []).map(
			(g) => g.name
		);
	}

	const suggestTags = async (q: string) =>
		((await api.GET('/api/v1/tags', { params: { query: { q } } })).data ?? []).map((t) => t.name);

	const dash = '—';
	const date = $derived(formatFullDate(song.release_date, song.release_date_precision));
</script>

<!-- The facts about the song in one container. The tags are the tiles of the page (`Descriptors`), so they have no row. -->
<section class="space-y-3 rounded-xl bg-card px-4 py-3" aria-label="Facts about the song">
	<dl>
		{#if draft}
			<FactRow label="Released">
				<ResetField
					edited={draft.edited('release_date')}
					bind:reset={draft.reset.date}
					label="date"
				>
					<PartialDateInput
						bind:value={draft.releaseDate}
						label="Release date"
						disabled={draft.reset.date}
					/>
				</ResetField>
			</FactRow>
		{:else}
			<FactRow label="Released">{date ?? 'No date'}</FactRow>
		{/if}
		<FactRow label="Language">{song.language ? languageName(song.language) : dash}</FactRow>
		<!-- One line: a long place is cut with "…", so the panel keeps its height. -->
		<FactRow label="Recorded">
			<span class="block truncate" title={song.recording_location ?? undefined}>
				{song.recording_location ?? dash}
			</span>
		</FactRow>
		<FactRow label="Views">
			{#if song.view_count}{formatCount(song.view_count)}{:else}{dash}{/if}
			{#if song.import_state === 'stub'}<Badge variant="warning">Stub: not imported in full</Badge
				>{/if}
		</FactRow>
	</dl>
	<dl>
		<FactRow label="Lyrics"><span class="capitalize">{song.lyrics_state ?? dash}</span></FactRow>
		<FactRow label="Content">
			{#if song.explicit || song.instrumental}
				{#if song.explicit}<Badge>Explicit</Badge>{/if}
				{#if song.instrumental}<Badge>Instrumental</Badge>{/if}
			{:else}{dash}{/if}
		</FactRow>
	</dl>
	<dl>
		{#if draft}
			<FactRow label="Genre">
				<ResetField edited={draft.edited('genre_id')} bind:reset={draft.reset.genre} label="genre">
					<Input
						bind:value={draft.genre}
						oninput={suggestGenres}
						list={genreListId}
						aria-label="Genre"
						placeholder="genre"
						disabled={draft.reset.genre}
						class="border-transparent"
					/>
					<datalist id={genreListId}>
						{#each genres as name (name)}<option value={name}></option>{/each}
					</datalist>
				</ResetField>
			</FactRow>
			<FactRow label="Tags">
				<ChipsEditor
					bind:values={draft.tags}
					label="the tags"
					placeholder="add a tag"
					suggest={suggestTags}
				/>
			</FactRow>
		{:else}
			<FactRow label="Genre">{song.genre ?? dash}</FactRow>
		{/if}
	</dl>
</section>
