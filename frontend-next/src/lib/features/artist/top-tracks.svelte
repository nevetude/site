<script lang="ts">
	import { resolve } from '$app/paths';
	import { api, type ArtistSong } from '#lib/api/client.js';
	import TrackRow from '#lib/components/track-row.svelte';
	import { Card } from '#lib/components/ui/card/index.js';
	import { PagedList } from '#lib/utils/paged.svelte.js';

	// `Artist` keeps credits (producer, writer) of other people's songs out of the "top"; an artist
	// who is only credited has no such role and gets all the songs.
	let { artistId, ownSongs }: { artistId: number; ownSongs: boolean } = $props();

	const COUNT = 10;
	const list = new PagedList<ArtistSong>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/songs', {
			params: {
				path: { artist_id: artistId },
				query: { roles: ownSongs ? ['Artist'] : [], sort: 'views', limit: COUNT, offset }
			}
		});
		return data;
	});

	$effect(() => {
		void list.reload();
	});
</script>

<!-- The popular tracks in the look of the tracklist of an album, without its numbers: the order is the order of views. -->
{#if list.items.length}
	<Card class="gap-0 py-2">
		<ul>
			{#each list.items as song (song.id)}
				<li>
					<TrackRow
						href={resolve('/songs/[id]', { id: String(song.id) })}
						thumb={song.cover_thumbnail_url}
						title={song.base_name}
						variant={song.variant}
						producers={{ names: song.producers.map((producer) => producer.base_name) }}
						views={song.view_count}
					/>
				</li>
			{/each}
		</ul>
	</Card>
{/if}
