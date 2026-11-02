<script lang="ts">
	import { api, type SongCard } from '#lib/api/client.js';
	import Thumb from '#lib/components/thumb.svelte';
	import SearchPick from '#lib/features/edit/search-pick.svelte';

	// Picks a song of the library by its name.
	let {
		label = 'Find a song',
		placeholder = 'add a song',
		onpick
	}: { label?: string; placeholder?: string; onpick: (song: SongCard) => void } = $props();

	async function search(q: string) {
		return (await api.GET('/api/v1/songs/search', { params: { query: { q } } })).data ?? [];
	}
</script>

<SearchPick {label} {placeholder} {search} {onpick}>
	{#snippet row(song: SongCard)}
		<Thumb src={song.cover_thumbnail_url} name={song.base_name} class="size-7 rounded-md" />
		<span class="min-w-0 flex-1 truncate text-left text-sm">
			{song.base_name}{#if song.variant}<span class="ml-1.5 text-muted-foreground"
					>{song.variant}</span
				>{/if}
		</span>
		<span class="truncate text-xs text-subtle">{song.artists.join(', ')}</span>
	{/snippet}
</SearchPick>
