<script lang="ts">
	import type { AlbumDetail } from '#lib/api/client.js';
	import CopyId from '#lib/components/copy-id.svelte';
	import Disclosure from '#lib/components/disclosure.svelte';

	let {
		album
	}: {
		album: Pick<AlbumDetail, 'cover_primary_color' | 'cover_secondary_color' | 'genius_id'>;
	} = $props();

	const swatches = $derived(
		[album.cover_primary_color, album.cover_secondary_color].filter((color) => color !== null)
	);
</script>

<Disclosure title="Debug data" open>
	<div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-subtle">
		{#each swatches as color, i (i)}
			<span class="flex items-center gap-1.5 font-mono">
				<span class="size-3.5 rounded-sm border border-border" style:background={color}></span>
				{color}
			</span>
		{/each}
		{#if album.genius_id !== null}<CopyId value={album.genius_id} />{/if}
	</div>
</Disclosure>
