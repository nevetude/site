<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import GripVertical from '@lucide/svelte/icons/grip-vertical';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '#lib/components/ui/button/index.js';
	import SongPick from '#lib/features/edit/song-pick.svelte';
	import { moved } from '#lib/utils/list.js';

	// The tracklist as a list to put in order (drag a row, or the arrows), to take tracks out of, and to add songs of the
	// library to. Nothing is deleted: a track that is taken out is only not shown on this album.
	export type DraftTrack = {
		key: number;
		song_id: number;
		name: string;
		variant: string | null;
		disc_number: number | null;
	};

	let { tracks = $bindable() }: { tracks: DraftTrack[] } = $props();

	let dragged = $state<number | null>(null);
	let nextKey = $state(-1); // the keys of tracks that are added: negative, so none is a key of a track of Genius

	// The numbers of the page: on each disc from 1.
	const numbers = $derived.by(() => {
		const on: Record<number, number> = {};
		return tracks.map((t) => (on[t.disc_number ?? 1] = (on[t.disc_number ?? 1] ?? 0) + 1));
	});
</script>

<div class="space-y-2 px-1 pb-2">
	<ol aria-label="Tracklist">
		{#each tracks as track, i (track.key)}
			<li
				draggable="true"
				ondragstart={() => (dragged = i)}
				ondragover={(event) => event.preventDefault()}
				ondrop={() => dragged !== null && ((tracks = moved(tracks, dragged, i)), (dragged = null))}
				ondragend={() => (dragged = null)}
				class="flex h-10 items-center gap-2 rounded-lg px-2 hover:bg-black/20 {dragged === i
					? 'opacity-40'
					: ''}"
			>
				<GripVertical class="size-4 shrink-0 cursor-grab text-subtle" aria-hidden="true" />
				<span class="w-5 shrink-0 text-center text-[10px] text-muted-foreground tabular-nums">
					{numbers[i]}
				</span>
				<span class="min-w-0 flex-1 truncate text-sm">
					{track.name}{#if track.variant}<span class="ml-1.5 text-muted-foreground"
							>{track.variant}</span
						>{/if}
				</span>
				{#if track.disc_number && track.disc_number > 1}
					<span class="text-xs text-subtle">disc {track.disc_number}</span>
				{/if}
				<Button
					variant="ghost"
					size="icon"
					aria-label="Move {track.name} up"
					disabled={i === 0}
					onclick={() => (tracks = moved(tracks, i, i - 1))}
				>
					<ChevronUp />
				</Button>
				<Button
					variant="ghost"
					size="icon"
					aria-label="Move {track.name} down"
					disabled={i === tracks.length - 1}
					onclick={() => (tracks = moved(tracks, i, i + 1))}
				>
					<ChevronDown />
				</Button>
				<Button
					variant="close"
					size="icon"
					aria-label="Take {track.name} off the album"
					onclick={() => (tracks = tracks.filter((t) => t !== track))}
				>
					<X />
				</Button>
			</li>
		{:else}
			<li class="p-3 text-center text-sm text-muted-foreground">No tracks</li>
		{/each}
	</ol>
	<div class="px-1">
		<SongPick
			label="Add a song to the album"
			onpick={(song) =>
				(tracks = [
					...tracks,
					{
						key: nextKey--,
						song_id: song.id,
						name: song.base_name,
						variant: song.variant,
						disc_number: tracks.at(-1)?.disc_number ?? null
					}
				])}
		/>
	</div>
</div>
