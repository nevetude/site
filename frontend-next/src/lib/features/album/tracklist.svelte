<script lang="ts">
	import Star from '@lucide/svelte/icons/star';
	import { resolve } from '$app/paths';
	import type { AlbumTrack } from '#lib/api/client.js';
	import CommaList from '#lib/components/comma-list.svelte';
	import TrackRow from '#lib/components/track-row.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { byDisc, differs, ofAlbum, popularity, trackNumbers } from '#lib/utils/albums.js';

	type Props = { tracks: AlbumTrack[]; artists: { id: number }[] };

	let { tracks, artists }: Props = $props();

	const discs = $derived(byDisc(tracks));
	const numbers = $derived(trackNumbers(tracks));
	// The most viewed track gets a filled star instead of its number, the second one an empty star.
	const rank = $derived(popularity(tracks));

	const names = (list: { base_name: string }[]) => list.map((a) => a.base_name);
</script>

{#if !tracks.length}
	<p class="p-3 text-center text-sm text-muted-foreground">No tracks</p>
{:else}
	{#each discs as disc (disc.number)}
		{#if discs.length > 1}
			<h3 class="pt-3 pb-1 pl-2 text-xs text-muted-foreground">Disc {disc.number}</h3>
		{/if}
		<ol>
			{#each disc.tracks as track (track.id)}
				{@const place = rank.get(track.song_id)}
				<!-- The artists of the album are known from the header: only a different line is worth showing. -->
				{@const second = differs(track.artists, artists)}
				<li>
					<TrackRow
						href={resolve('/songs/[id]', { id: String(track.song_id) })}
						thumb={track.cover_thumbnail_url}
						title={track.base_name}
						variant={track.variant}
						producers={{
							names: names(track.producers),
							tinted: ofAlbum(track.producers, artists)
						}}
						views={track.view_count}
						viewsTitle={place ? `Top ${place} by views` : undefined}
						explicit={!!track.explicit}
					>
						{#snippet lead()}
							<span class="text-center text-muted-foreground">
								{#if place === 1}
									<span title="The most viewed track" class="inline-flex align-middle">
										<Star class="size-[8.5px] fill-current" aria-label="The most viewed track" />
									</span>
								{:else if place === 2}
									<span title="Top 2 by views" class="inline-flex align-middle">
										<Star class="size-[8.5px]" aria-label="Top 2 by views" />
									</span>
								{:else}
									<span class="text-[10px] tabular-nums">{numbers[track.id]}</span>
								{/if}
							</span>
						{/snippet}
						{#snippet inline()}
							{#if track.featured.length}
								<span class="min-w-0 shrink-[3] truncate text-xs text-muted-foreground">
									feat. <CommaList
										items={names(track.featured)}
										wrap={false}
										tinted={ofAlbum(track.featured, artists)}
									/>
								</span>
							{/if}
							{#if track.import_state === 'stub'}<Badge>Stub</Badge>{/if}
						{/snippet}
						{#snippet sub()}
							{#if second}
								<CommaList
									items={names(track.artists)}
									wrap={false}
									tinted={ofAlbum(track.artists, artists)}
								/>
							{/if}
						{/snippet}
					</TrackRow>
				</li>
			{/each}
		</ol>
	{/each}
{/if}
