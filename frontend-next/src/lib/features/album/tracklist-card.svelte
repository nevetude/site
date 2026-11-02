<script lang="ts">
	import type { AlbumDetail, AlbumTrack } from '#lib/api/client.js';
	import type { AlbumDraft } from '#lib/features/album/album-draft.svelte.js';
	import Tracklist from '#lib/features/album/tracklist.svelte';
	import TracklistEditor from '#lib/features/album/tracklist-editor.svelte';

	// `draft`: the page is being edited, and the tracks are a list to put in order.
	let {
		album,
		tracks,
		tint,
		draft = $bindable(null)
	}: {
		album: AlbumDetail;
		tracks: AlbumTrack[];
		tint: string | undefined;
		draft?: AlbumDraft | null;
	} = $props();
</script>

<!-- The colour of the cover, darker than the cards around it; without a cover the colour of a card. -->
<section class="rounded-xl bg-card pt-3 pb-1" style:background-color={tint}>
	{#if draft}
		<TracklistEditor bind:tracks={draft.tracks} />
	{:else}
		<Tracklist {tracks} artists={album.artists} />
	{/if}
</section>
