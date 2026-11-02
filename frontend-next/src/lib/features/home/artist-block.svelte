<script lang="ts">
	import { api, type ArtistCard as ArtistCardData, type RoleCount } from '#lib/api/client.js';
	import ListSection from '#lib/components/list-section.svelte';
	import RoleFilter from '#lib/components/role-filter.svelte';
	import SectionHeader from '#lib/components/section-header.svelte';
	import SortMenu from '#lib/components/sort-menu.svelte';
	import ArtistCard from '#lib/features/home/artist-card.svelte';
	import { SORTS, type Block, type SortField } from '#lib/features/home/artists.js';
	import { PagedList } from '#lib/utils/paged.svelte.js';
	import type { Order } from '#lib/utils/sort.js';

	let { block }: { block: Block } = $props();

	const PAGE = 60;

	let sort = $state<SortField>('tracks');
	let order = $state<Order | null>(null);
	let selected = $state<string[]>([]);
	let roles = $state<RoleCount[]>([]);

	const list = new PagedList<ArtistCardData>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists', {
			params: {
				query: {
					...block.filters,
					roles: selected,
					sort,
					order: order ?? undefined,
					limit: PAGE,
					offset
				}
			}
		});
		return data;
	});

	// A new sort or a new set of roles starts the list again from the top.
	$effect(() => {
		void [sort, order, selected];
		void list.reload();
	});

	$effect(() => {
		void api
			.GET('/api/v1/artists/roles', { params: { query: block.filters } })
			.then(({ data }) => (roles = data ?? []));
	});
</script>

<section class="space-y-3">
	<SectionHeader title={block.title} count={list.total}>
		{#snippet actions()}<SortMenu options={SORTS} bind:sort bind:order />{/snippet}
	</SectionHeader>

	<RoleFilter roles={roles.map(({ role, artists }) => ({ role, count: artists }))} bind:selected />

	<ListSection {list} failed="The list did not load. Is the backend running?" empty="No artists">
		<div class="grid grid-cols-[repeat(auto-fill,minmax(14.875rem,1fr))] gap-3">
			{#each list.items as artist (artist.id)}
				<ArtistCard {artist} />
			{/each}
		</div>
	</ListSection>
</section>
