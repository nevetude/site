<script lang="ts">
	import { resolve } from '$app/paths';

	// Names of artists as links, separated by grey commas. No <wbr>: it would let a one-line text break.
	type Props = { artists: { id: number; base_name: string }[]; tinted?: boolean };

	let { artists, tinted = false }: Props = $props();
</script>

{#each artists as artist, i (artist.id)}{#if i}<span class="mr-[0.3em] text-subtle">,</span>{/if}<a
		href={resolve('/artists/[id]', { id: String(artist.id) })}
		class={tinted ? 'text-(--artist-color)' : ''}>{artist.base_name}</a
	>{/each}
