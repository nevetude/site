<script lang="ts">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import X from '@lucide/svelte/icons/x';
	import ArtistPick from '#lib/features/edit/artist-pick.svelte';
	import { moved } from '#lib/utils/list.js';

	// A list of artists in the order they are shown (the artists of a song, or its guests): each can be moved along the
	// list and taken out, and an artist of the library is added by search.
	export type DraftArtist = { id: number; base_name: string };

	let { artists = $bindable(), label }: { artists: DraftArtist[]; label: string } = $props();
</script>

<div class="space-y-1.5">
	<ul class="flex flex-wrap gap-1.5" aria-label={label}>
		{#each artists as artist, i (artist.id)}
			<li class="inline-flex items-center gap-0.5 rounded-md bg-muted px-1.5 py-0.5 text-sm">
				<button
					type="button"
					class="text-subtle hover:text-foreground disabled:opacity-30"
					aria-label="Move {artist.base_name} earlier"
					disabled={i === 0}
					onclick={() => (artists = moved(artists, i, i - 1))}
					><ChevronLeft class="size-3.5" /></button
				>
				<span class="px-1">{artist.base_name}</span>
				<button
					type="button"
					class="text-subtle hover:text-foreground disabled:opacity-30"
					aria-label="Move {artist.base_name} later"
					disabled={i === artists.length - 1}
					onclick={() => (artists = moved(artists, i, i + 1))}
					><ChevronRight class="size-3.5" /></button
				>
				<button
					type="button"
					class="text-subtle hover:text-destructive"
					aria-label="Take {artist.base_name} out of {label}"
					onclick={() => (artists = artists.filter((a) => a !== artist))}
					><X class="size-3.5" /></button
				>
			</li>
		{/each}
	</ul>
	<ArtistPick
		label="Add to {label}"
		placeholder="add an artist"
		onpick={(artist) => {
			if (artists.some((a) => a.id === artist.id)) return;
			artists = [...artists, { id: artist.id, base_name: artist.base_name }];
		}}
	/>
</div>
