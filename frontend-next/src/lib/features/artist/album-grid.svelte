<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import LayoutList from '@lucide/svelte/icons/layout-list';
	import { api, type ArtistAlbum, type SeriesOut, type WorkRoleCount } from '#lib/api/client.js';
	import ListSection from '#lib/components/list-section.svelte';
	import RoleFilter, { chip } from '#lib/components/role-filter.svelte';
	import SortMenu from '#lib/components/sort-menu.svelte';
	import * as ToggleGroup from '#lib/components/ui/toggle-group/index.js';
	import AlbumCategory from '#lib/features/album/album-category.svelte';
	import { onDestroy } from 'svelte';
	import type { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';
	import SeriesBlock from '#lib/features/artist/series-block.svelte';
	import { ReleaseDrag } from '#lib/features/artist/release-drag.svelte.js';
	import { PagedList } from '#lib/utils/paged.svelte.js';
	import { BY_NAME, BY_RELEASED, BY_VIEWS, type Order } from '#lib/utils/sort.js';

	// `draft`: the edit mode of the page. The releases are dragged between the kinds of release; a kind is changed on the
	// draft at once and written when the page is saved.
	let {
		artistId,
		roles,
		series,
		draft = $bindable(null)
	}: {
		artistId: number;
		roles: WorkRoleCount[];
		series: SeriesOut[];
		draft?: ArtistDraft | null;
	} = $props();

	const PAGE = 200; // the most one call gives; an artist has a few hundred albums at most
	const SORTS = [BY_RELEASED, BY_NAME, BY_VIEWS];
	// The kinds of release Genius knows, in the order a discography is read.
	const CATEGORIES = [
		{ type: 'album', title: 'Albums' },
		{ type: 'mixtape', title: 'Mixtapes' },
		{ type: 'ep', title: 'EPs' },
		{ type: 'single', title: 'Singles' },
		{ type: 'compilation', title: 'Compilations' },
		{ type: 'soundtrack', title: 'Soundtracks' },
		{ type: 'live', title: 'Live' },
		{ type: 'dj_mix', title: 'DJ mixes' },
		{ type: 'other', title: 'Other' }
	];
	const KNOWN = new Set(CATEGORIES.map((category) => category.type));

	let sort = $state<(typeof SORTS)[number]['value']>('released');
	let order = $state<Order | null>(null);
	let selected = $state<string[]>([]);
	let unreleased = $state(false);
	let openAll = $state(false);
	let view = $state<'grid' | 'list'>('grid');

	const list = new PagedList<ArtistAlbum>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/albums', {
			params: {
				path: { artist_id: artistId },
				query: {
					roles: selected,
					include_unreleased: unreleased,
					sort,
					order: order ?? undefined,
					limit: PAGE,
					offset
				}
			}
		});
		return data;
	});

	// All the albums are loaded, because the categories are made here and each one needs all of its own.
	// Pressing Unreleased brings the albums that are not out yet; the strips with such albums are scrolled to their end,
	// where they are (the albums with no date come last), once the list has them.
	let wasUnreleased = false;
	let toEnd = $state(0);
	$effect(() => {
		void [sort, order, selected];
		const turnedOn = unreleased && !wasUnreleased;
		wasUnreleased = unreleased;
		void list.reload(true).then(() => {
			if (turnedOn) toEnd++;
		});
	});

	// A type Genius adds one day (or none at all) goes to "Other".
	const kindOf = (album: ArtistAlbum) =>
		album.album_type && KNOWN.has(album.album_type) ? album.album_type : 'other';

	// The kind a release has on the page: the one it was dragged to, else its own.
	const typeOf = (album: ArtistAlbum) => draft?.albumTypes[album.id] ?? kindOf(album);

	// In the edit mode every kind is there, also an empty one: a release can be dragged to it.
	const groups = $derived(
		CATEGORIES.map(({ type, title }) => ({
			type,
			title,
			albums: list.items.filter((album) => typeOf(album) === type)
		})).filter((group) => draft || group.albums.length)
	);

	// A kind takes the release away from its old kind; a series only gets a copy (and keeps the one it had).
	const drag = new ReleaseDrag((album, type, from) => {
		if (!draft) return false;
		if (type.startsWith('series:')) return draft.addToSeries(Number(type.slice(7)), album);
		if (from.startsWith('series:')) return false;
		const next = { ...draft.albumTypes };
		if (kindOf(album) === type) delete next[album.id];
		else next[album.id] = type;
		draft.albumTypes = next;
	});
	onDestroy(() => drag.destroy());

	// The page is read again when the edit mode ends: what was saved shows as it is on the server.
	let wasEditing = false;
	$effect(() => {
		const editing = draft !== null;
		if (wasEditing && !editing) void list.reload(true);
		wasEditing = editing;
	});
</script>

<section class="space-y-4 rounded-xl bg-card p-5">
	<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
		<!-- Like the name of a category: the title with its chevron opens or closes every list at once. -->
		<button
			type="button"
			aria-expanded={openAll}
			title="{openAll ? 'Hide' : 'Show'} all lists ({list.items.length} releases)"
			class="flex items-center gap-1.5 hover:text-white"
			onclick={() => (openAll = !openAll)}
		>
			<h2 class="text-base font-semibold">Releases</h2>
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

	<RoleFilter roles={roles.map(({ role, works }) => ({ role, count: works }))} bind:selected>
		{#snippet end()}
			<button
				type="button"
				aria-pressed={unreleased}
				class={chip(unreleased)}
				onclick={() => (unreleased = !unreleased)}
			>
				Unreleased
			</button>
		{/snippet}
	</RoleFilter>

	<ListSection {list} failed="The albums did not load." empty="No albums" more={false}>
		<div class="space-y-2.5">
			{#each groups as group (group.type)}
				<AlbumCategory
					type={group.type}
					scrollEnd={toEnd}
					markUnreleased
					drag={draft ? drag : null}
					title={group.title}
					albums={group.albums}
					{view}
					{openAll}
					resetKey="{sort}|{order}|{selected.join()}"
					showViews={sort === 'views'}
				/>
			{/each}
		</div>
	</ListSection>
</section>

<SeriesBlock {artistId} {series} {draft} {drag} albums={list.items} />
