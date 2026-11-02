<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import { fade } from 'svelte/transition';
	import { api, type ArtistVideo } from '#lib/api/client.js';
	import ListSection from '#lib/components/list-section.svelte';
	import SectionHeader from '#lib/components/section-header.svelte';
	import SortMenu from '#lib/components/sort-menu.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import VideoTile from '#lib/components/video-tile.svelte';
	import { youtubeClip, youtubeEmbedUrl } from '#lib/utils/dom.js';
	import { formatCount } from '#lib/utils/format.js';
	import { PagedList } from '#lib/utils/paged.svelte.js';
	import { BY_NAME, BY_RELEASED, BY_VIEWS, type Order } from '#lib/utils/sort.js';

	let { artistId }: { artistId: number } = $props();

	const PAGE = 12;
	const SORTS = [BY_RELEASED, BY_NAME, BY_VIEWS];

	// The most viewed clips first; the menu still has the other orders.
	let sort = $state<(typeof SORTS)[number]['value']>('views');
	let order = $state<Order | null>(null);
	let playing = $state<string | null>(null);
	let loading = $state(false); // the player of the clip that was pressed is still loading

	const list = new PagedList<ArtistVideo>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/videos', {
			params: {
				path: { artist_id: artistId },
				query: { sort, order: order ?? undefined, limit: PAGE, offset }
			}
		});
		return data;
	});

	$effect(() => {
		void [sort, order];
		void list.reload();
	});

	// Only YouTube is embedded; a clip on another site has nothing to show here.
	const clips = $derived(
		list.items.flatMap((video) => {
			const clip = youtubeClip(video.url, video.start_seconds);
			return clip ? [{ ...video, ...clip }] : [];
		})
	);
	const current = $derived(clips.find((clip) => clip.url === playing));
</script>

<!-- Empty (no clips at all, or none loaded yet): the block is not on the page. -->
{#if list.total > 0}
	<section class="space-y-3">
		<SectionHeader title="Videos" count={list.total}>
			{#snippet actions()}<SortMenu options={SORTS} bind:sort bind:order />{/snippet}
		</SectionHeader>

		{#if current}
			<div class="relative aspect-video max-w-3xl overflow-hidden rounded-lg bg-black">
				<iframe
					src={youtubeEmbedUrl(current.id, current.start, { autoplay: '1' })}
					title={current.song_name}
					allow="autoplay; fullscreen"
					referrerpolicy="strict-origin-when-cross-origin"
					class="absolute inset-0 size-full"
					onload={() => (loading = false)}
				></iframe>
				<!-- Until the player of the clip has loaded: a spinner turns over the black. -->
				{#if loading}
					<div
						class="pointer-events-none absolute inset-0 flex items-center justify-center"
						transition:fade={{ duration: 200 }}
					>
						<Spinner class="size-10 stroke-3 text-white" aria-label="The clip is loading" />
					</div>
				{/if}
				<Button
					variant="close"
					size="icon"
					class="absolute top-2 right-2 rounded-full bg-black/40 hover:bg-black/70"
					aria-label="Close the clip"
					onclick={() => (playing = null)}
				>
					<X />
				</Button>
			</div>
		{/if}

		<ListSection {list} failed="The videos did not load." empty="No videos">
			<ul class="grid grid-cols-[repeat(auto-fill,minmax(12.25rem,1fr))] gap-3">
				{#each clips as clip (clip.url)}
					<li>
						<VideoTile
							picture={clip.picture}
							label="Play {clip.song_name}"
							current={clip.url === playing}
							onplay={() => {
								playing = clip.url;
								loading = true;
							}}
						>
							<div class="truncate text-xs" title={clip.song_name}>
								{clip.song_name}{#if clip.variant}<span class="text-subtle">
										{clip.variant}</span
									>{/if}
							</div>
							<div
								class="mt-0.5 flex h-4 items-baseline gap-2 text-[11px] leading-4 text-muted-foreground"
							>
								<span class="min-w-0 flex-1 truncate">{clip.artists.join(', ')}</span>
								{#if clip.view_count}
									<span class="shrink-0 tabular-nums">{formatCount(clip.view_count)}</span>
								{/if}
								{#if clip.release_date}
									<span class="shrink-0 tabular-nums">{clip.release_date.slice(0, 4)}</span>
								{/if}
							</div>
						</VideoTile>
					</li>
				{/each}
			</ul>
		</ListSection>
	</section>
{/if}
