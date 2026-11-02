<script lang="ts">
	import { resolve } from '$app/paths';
	import type { RelatedSongs } from '#lib/api/client.js';
	import CommaList from '#lib/components/comma-list.svelte';
	import TrackRow from '#lib/components/track-row.svelte';
	import { Card } from '#lib/components/ui/card/index.js';
	import { songRelationTitle } from '#lib/features/song/song.js';

	let { related }: { related: RelatedSongs[] } = $props();
</script>

<!-- The songs this one is tied to (samples, remixes, covers), a list per kind of tie, in the look of the rows of a tracklist. -->
<Card class="gap-3 p-4">
	{#each related as group (`${group.type}:${group.inverse}`)}
		<div class="space-y-1">
			<h3 class="text-sm font-medium">{songRelationTitle(group)}</h3>
			<ul>
				{#each group.songs as song (song.id)}
					<li>
						<TrackRow
							href={resolve('/songs/[id]', { id: String(song.id) })}
							thumb={song.cover_thumbnail_url}
							title={song.base_name}
							variant={song.variant}
							class="-mx-1.5 px-1.5"
						>
							{#snippet sub()}<CommaList items={song.artists} wrap={false} />{/snippet}
						</TrackRow>
					</li>
				{/each}
			</ul>
		</div>
	{/each}
</Card>
