<script lang="ts">
	import type { ArtistDetail } from '#lib/api/client.js';
	import ClampList from '#lib/components/clamp-list.svelte';

	let { genres }: { genres: ArtistDetail['genres'] } = $props();
</script>

<!-- The genres of the songs of the artist as tiles with the number of songs; two rows, the rest opens over the page. -->
{#if genres.length}
	<ClampList items={genres} lines={2} tiles float>
		{#snippet item({ genre, songs })}<span
				class="inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 text-xs whitespace-nowrap text-foreground"
				>{genre}<span class="font-mono text-subtle">{songs}</span></span
			>{/snippet}
	</ClampList>
{/if}
