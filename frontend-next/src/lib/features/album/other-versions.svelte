<script lang="ts">
	import type { RelatedAlbums } from '#lib/api/client.js';
	import AlbumCategory from '#lib/features/album/album-category.svelte';
	import { relationTitle } from '#lib/utils/albums.js';

	let { related }: { related: RelatedAlbums[] } = $props();
</script>

<!-- Like the releases of an artist: a strip per kind of version, two albums in view, the rest by scrolling. -->
<section class="space-y-4 rounded-xl bg-card p-4">
	{#each related as group (`${group.type}:${group.inverse}`)}
		<AlbumCategory
			albums={group.albums}
			view="grid"
			openAll={false}
			resetKey=""
			columns={2}
			note={relationTitle(group)}
		/>
	{/each}
</section>
