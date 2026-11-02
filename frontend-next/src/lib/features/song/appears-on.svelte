<script lang="ts">
	import type { SongDetail } from '#lib/api/client.js';
	import AlbumCategory from '#lib/features/album/album-category.svelte';

	let { albums }: { albums: SongDetail['albums'] } = $props();
</script>

<!-- Like the other versions of an album (`OtherVersions`), but open from the start (the chevron closes it): two albums in a row, all of them shown. -->
<section class="space-y-4 rounded-xl bg-card p-4">
	<AlbumCategory
		title="Appears on"
		albums={albums.map((placement) => placement.album)}
		view="grid"
		openAll={false}
		startOpen
		resetKey=""
		columns={2}
	/>
</section>
