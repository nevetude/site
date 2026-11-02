<script lang="ts">
	import { BLOCKS } from '#lib/features/home/artists.js';
	import ArtistBlock from '#lib/features/home/artist-block.svelte';
</script>

<div class="space-y-10">
	{#each BLOCKS as block (block.id)}
		<ArtistBlock {block} />
	{/each}
</div>
