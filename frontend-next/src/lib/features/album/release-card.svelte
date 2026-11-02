<script lang="ts">
	import type { AlbumDetail } from '#lib/api/client.js';
	import CoverPanel from '#lib/components/cover-panel.svelte';
	import AlbumCover from '#lib/features/album/album-cover.svelte';
	import CoverViewer from '#lib/features/album/cover-viewer.svelte';
	import type { CoverDraft } from '#lib/features/edit/cover-editor.svelte';
	import CoverControls from '#lib/features/edit/cover-controls.svelte';
	import { coverTint, type Cover } from '#lib/utils/albums.js';

	// Only the colour of the cover is read: a song has one too. `draft`: the page is being edited, and the cover can be
	// changed; the panel shows the cover that was chosen.
	type Props = {
		album: Pick<AlbumDetail, 'cover_secondary_color'>;
		covers: Cover[];
		draft?: CoverDraft | null;
	};

	let { album, covers, draft = $bindable(null) }: Props = $props();

	let viewing = $state(false); // the covers are open in the overlay
	let index = $state(0); // which one
	const chosen = $derived<Cover | null>(
		draft?.cover ? { url: draft.cover.url, thumb: draft.cover.thumbnail } : null
	);
	const shown = $derived(
		chosen ? [chosen, ...covers.filter((cover) => cover.url !== chosen.url)] : covers
	);
	// A cover that was chosen has no colours of Genius.
	const tint = $derived(chosen ? undefined : coverTint(album));
</script>

<CoverPanel {tint}>
	{#snippet back()}
		{#if draft}<CoverControls bind:draft noun="cover" known={covers} />{/if}
	{/snippet}
	<AlbumCover
		covers={shown}
		onopen={() => {
			index = 0;
			viewing = true;
		}}
	/>
</CoverPanel>

{#if viewing}
	<CoverViewer
		covers={shown.filter((cover) => !cover.placeholder)}
		bind:index
		onclose={() => (viewing = false)}
	/>
{/if}
