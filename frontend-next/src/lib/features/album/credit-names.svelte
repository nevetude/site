<script lang="ts">
	import { resolve } from '$app/paths';
	import type { CreditGroup } from '#lib/api/client.js';
	import ClampList from '#lib/components/clamp-list.svelte';

	// `main`: the artists of the album, in whatever role they are credited their name gets the tint of the cover.
	let { artists, main }: { artists: CreditGroup['artists']; main: { id: number }[] } = $props();
</script>

<ClampList items={artists} lines={2}>
	{#snippet item({ artist, tracks })}
		<a
			href={resolve('/artists/[id]', { id: String(artist.id) })}
			title={tracks === null ? undefined : `${tracks} ${tracks === 1 ? 'track' : 'tracks'}`}
			class={main.some(({ id }) => id === artist.id) ? 'text-(--artist-color)' : ''}
			>{artist.base_name}</a
		>
	{/snippet}
</ClampList>
