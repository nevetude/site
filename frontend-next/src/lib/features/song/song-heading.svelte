<script lang="ts">
	import type { SongDetail } from '#lib/api/client.js';
	import ArtistListEditor from '#lib/features/edit/artist-list-editor.svelte';
	import TitleFields from '#lib/features/edit/title-fields.svelte';
	import type { SongDraft } from '#lib/features/song/song-draft.svelte.js';
	import ArtistLinks from '#lib/components/artist-links.svelte';
	import EntityTitle from '#lib/components/entity-title.svelte';
	import ExplicitMark from '#lib/components/explicit-mark.svelte';

	// `draft`: the page is being edited, and the title and the artists are fields.
	let { song, draft = $bindable(null) }: { song: SongDetail; draft?: SongDraft | null } = $props();

	const tooltip = $derived(
		[song.base_name, song.variant, song.disambiguator].filter(Boolean).join(' ')
	);
</script>

{#snippet editTitle()}
	<TitleFields bind:draft placeholder="subtitle, for example Remix" />
{/snippet}

<!-- The title of the song and its artists: what stands at the top of the header, with or without a container around it. -->
<EntityTitle
	title={song.base_name}
	{tooltip}
	genius={song.genius_url}
	edit={draft ? editTitle : undefined}
>
	{#snippet after()}
		{#if song.variant}<span class="font-normal text-subtle">{song.variant}</span>{/if}
		{#if song.explicit}<ExplicitMark class="ml-2 inline-block size-4 text-muted-foreground" />{/if}
		{#if song.disambiguator}
			<span class="text-base font-normal text-subtle">{song.disambiguator}</span>
		{/if}
	{/snippet}
	{#if !draft}
		<ArtistLinks artists={song.artists} tinted />
		{#if song.featured.length}
			<span class="mx-[0.3em] text-muted-foreground">feat.</span>
			<ArtistLinks artists={song.featured} />
		{/if}
	{/if}
</EntityTitle>
{#if draft}
	<div class="mt-3 space-y-2">
		<ArtistListEditor bind:artists={draft.artists} label="the artists" />
		<span class="text-xs text-subtle">feat.</span>
		<ArtistListEditor bind:artists={draft.featured} label="the guests" />
	</div>
{/if}
