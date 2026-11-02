<script lang="ts">
	import { api, type ArtistRef } from '#lib/api/client.js';
	import Thumb from '#lib/components/thumb.svelte';
	import SearchPick from '#lib/features/edit/search-pick.svelte';

	// Picks an artist of the library by any of their names (one that is not in the library has to be imported first).
	let {
		label = 'Find an artist',
		placeholder = 'add an artist',
		onpick
	}: { label?: string; placeholder?: string; onpick: (artist: ArtistRef) => void } = $props();

	async function search(q: string) {
		return (await api.GET('/api/v1/artists/search', { params: { query: { q } } })).data ?? [];
	}
</script>

<SearchPick {label} {placeholder} {search} {onpick}>
	{#snippet row(artist: ArtistRef)}
		<Thumb src={artist.cover_url} name={artist.base_name} class="size-7 rounded-md" />
		<span class="min-w-0 flex-1 truncate text-left text-sm">{artist.base_name}</span>
		<span class="text-xs text-subtle tabular-nums">{artist.genius_id ?? ''}</span>
	{/snippet}
</SearchPick>
