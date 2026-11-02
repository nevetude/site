<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import LayoutList from '@lucide/svelte/icons/layout-list';
	import Wand from '@lucide/svelte/icons/wand-sparkles';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { api, type ArtistAlbum, type SeriesOut } from '#lib/api/client.js';
	import CoverPlaceholder from '#lib/components/cover-placeholder.svelte';
	import ExplicitEye from '#lib/components/explicit-eye.svelte';
	import SortMenu from '#lib/components/sort-menu.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import AlbumCategory from '#lib/features/album/album-category.svelte';
	import type { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';
	import type { ReleaseDrag } from '#lib/features/artist/release-drag.svelte.js';
	import SearchPick from '#lib/features/edit/search-pick.svelte';
	import { cellsPerRow, isDefaultCover } from '#lib/utils/albums.js';
	import { findSeries } from '#lib/utils/find-series.js';
	import { formatRelease } from '#lib/utils/format.js';
	import { BY_NAME, BY_RELEASED, BY_VIEWS, type Order } from '#lib/utils/sort.js';
	import { watchWidth } from '#lib/utils/watch-size.js';

	// The series of the artist, a block of its own like the releases: the same strips, chevrons, view and sort. A release
	// stays in its kind and is in the series too; in the edit mode it is dragged here from the kinds (a copy), or found
	// by name, and a cross takes it out again.
	type Props = {
		artistId: number;
		series: SeriesOut[];
		draft: ArtistDraft | null;
		drag: ReleaseDrag;
		albums: ArtistAlbum[]; // the releases of the page, where the series are looked for
	};

	let { artistId, series, draft, drag, albums }: Props = $props();

	const SORTS = [BY_RELEASED, BY_NAME, BY_VIEWS];
	let sort = $state<(typeof SORTS)[number]['value']>('released');
	let order = $state<Order | null>('asc'); // a series is read from its oldest release to the newest
	let openAll = $state(false);
	let view = $state<'grid' | 'list'>('grid');

	// The server and the draft keep a series by date; the other sortings are made here, on the releases it has.
	function sorted(albums: ArtistAlbum[]) {
		const first = SORTS.find((s) => s.value === sort)!.first;
		const flip = (order ?? first) === first ? 1 : -1;
		const by = {
			released: (a: ArtistAlbum, b: ArtistAlbum) =>
				(b.release_date ?? '').localeCompare(a.release_date ?? ''),
			name: (a: ArtistAlbum, b: ArtistAlbum) => a.base_name.localeCompare(b.base_name),
			views: (a: ArtistAlbum, b: ArtistAlbum) => (b.view_count ?? 0) - (a.view_count ?? 0)
		}[sort];
		return albums.toSorted((a, b) => flip * by(a, b) || a.id - b.id);
	}

	// The fields of a series stand on the grid of the cards below them: the name takes the first cell up to the gap, so the
	// button begins where the cover of the second card does (the cover is 10.5px inside its card, the gap is 14px).
	let rowWidth = $state(0);
	const nameWidth = $derived(rowWidth ? rowWidth / cellsPerRow(rowWidth) - 3.5 : 154);

	const shown = $derived(draft ? draft.series : series.map((s, key) => ({ key, ...s })));
	const count = $derived(shown.reduce((sum, s) => sum + s.albums.length, 0));

	async function find(text: string): Promise<ArtistAlbum[]> {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/albums', {
			params: {
				path: { artist_id: artistId },
				query: { q: text, include_unreleased: true, sort: 'released', limit: 10 }
			}
		});
		return data?.items ?? [];
	}
</script>

{#if shown.length || draft}
	<section class="space-y-4 rounded-xl bg-card p-5">
		<!-- The header with the view and the sort is for reading: the edit mode has only the fields of the series. -->
		{#if count && !draft}
			<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
				<button
					type="button"
					aria-expanded={openAll}
					title="{openAll ? 'Hide' : 'Show'} all lists ({count} releases)"
					class="flex items-center gap-1.5 hover:text-white"
					onclick={() => (openAll = !openAll)}
				>
					<h2 class="text-base font-semibold">Series</h2>
					{#if openAll}<ChevronDown class="size-4 text-muted-foreground" />{:else}<ChevronRight
							class="size-4 text-muted-foreground"
						/>{/if}
				</button>
				<div class="ml-auto flex items-center gap-2">
					<ToggleGroup.Root
						value={view}
						onValueChange={(next) => next && (view = next as typeof view)}
						aria-label="View"
					>
						<ToggleGroup.Item value="grid" aria-label="Grid" title="Grid">
							<LayoutGrid />
						</ToggleGroup.Item>
						<ToggleGroup.Item
							value="list"
							aria-label="Rows: the cover with its details beside it"
							title="Rows: the cover with its details beside it"
						>
							<LayoutList />
						</ToggleGroup.Item>
					</ToggleGroup.Root>
					<SortMenu options={SORTS} bind:sort bind:order />
				</div>
			</header>
		{/if}

		<div class="space-y-5">
			{#each shown as one, index (one.key)}
				{@const key = `series:${one.key}`}
				<div
					class="space-y-2 rounded-xl transition-colors duration-200 {draft && drag.over === key
						? 'bg-foreground/10'
						: ''}"
					data-category={draft ? key : undefined}
				>
					{#if draft}
						<!-- In the place of the title of the series: its name to type, and the search for releases beside it. -->
						<div class="flex items-start gap-4" use:watchWidth={(w) => (rowWidth = w)}>
							<div style:width="{nameWidth}px" class="shrink-0">
								<Input
									bind:value={draft.series[draft.series.findIndex((s) => s.key === one.key)].name}
									aria-label="Name of the series"
									placeholder="Name of the series"
								/>
							</div>
							<div class="w-[154px]">
								<SearchPick
									label="Find a release to add"
									button="Release"
									search={find}
									onpick={(album) => draft.addToSeries(one.key, album)}
								>
									{#snippet row(album)}
										{#if isDefaultCover(album.cover_thumbnail_url)}
											<span class="relative size-8 shrink-0 overflow-hidden rounded">
												<CoverPlaceholder class="size-4" />
											</span>
										{:else if album.cover_thumbnail_url}
											<span class="relative size-8 shrink-0 overflow-hidden rounded">
												<img
													src={album.cover_thumbnail_url}
													alt=""
													class="size-full object-cover {album.cover_explicit
														? 'scale-110 blur-xs'
														: ''}"
												/>
												{#if album.cover_explicit}<ExplicitEye class="size-4" />{/if}
											</span>
										{:else}
											<span class="size-8 shrink-0 rounded bg-background"></span>
										{/if}
										<span class="min-w-0 truncate">
											{album.base_name}
											{#if album.variant}<span class="text-subtle">{album.variant}</span>{/if}
										</span>
										<span class="ml-auto shrink-0 text-xs text-subtle">
											{formatRelease(album.release_date, 'year')}
										</span>
									{/snippet}
								</SearchPick>
							</div>
							<Button
								variant="close"
								size="icon"
								class="bg-accent"
								aria-label="Delete the series"
								title="Delete the series"
								onclick={() => draft.removeSeries(one.key)}
							>
								<Trash2 />
							</Button>
							{#if index === 0}
								<Button
									variant="ghost"
									class="ml-auto gap-1"
									title="Looks for releases whose titles share a stem (Part I, Part II, ...)"
									onclick={() => draft.addFound(findSeries(albums))}
								>
									<Wand class="size-4" /> Find series
								</Button>
							{/if}
						</div>
					{/if}
					{#if one.albums.length || !draft}
						<AlbumCategory
							type={key}
							title={draft ? undefined : one.name}
							albums={sorted(one.albums)}
							{view}
							{openAll}
							markUnreleased
							showViews={sort === 'views'}
							drag={draft ? drag : null}
							remove={draft ? (album) => draft.removeFromSeries(one.key, album.id) : undefined}
							resetKey="{one.key}|{sort}|{order}"
						/>
					{/if}
				</div>
			{/each}
		</div>
	</section>
{/if}
