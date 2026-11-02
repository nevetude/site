<script lang="ts">
	import PanelTop from '@lucide/svelte/icons/panel-top';
	import { api, type ArtistSong, type WorkRoleCount } from '#lib/api/client.js';
	import ListSection from '#lib/components/list-section.svelte';
	import RoleFilter from '#lib/components/role-filter.svelte';
	import SectionHeader from '#lib/components/section-header.svelte';
	import SongTitle from '#lib/components/song-title.svelte';
	import SortMenu from '#lib/components/sort-menu.svelte';
	import Thumb from '#lib/components/thumb.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { formatCount, formatRelease } from '#lib/utils/format.js';
	import { PagedList } from '#lib/utils/paged.svelte.js';
	import { BY_NAME, BY_RELEASED, BY_VIEWS, type Order } from '#lib/utils/sort.js';

	let { artistId, roles }: { artistId: number; roles: WorkRoleCount[] } = $props();

	const PAGE = 60;
	const SORTS = [BY_RELEASED, BY_NAME, BY_VIEWS];

	let sort = $state<(typeof SORTS)[number]['value']>('released');
	let order = $state<Order | null>(null);
	let selected = $state<string[]>([]);

	const list = new PagedList<ArtistSong>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/songs', {
			params: {
				path: { artist_id: artistId },
				query: { roles: selected, sort, order: order ?? undefined, limit: PAGE, offset }
			}
		});
		return data;
	});

	$effect(() => {
		void [sort, order, selected];
		void list.reload();
	});
</script>

<section class="space-y-3">
	<SectionHeader title="Songs" count={list.total}>
		{#snippet actions()}<SortMenu options={SORTS} bind:sort bind:order />{/snippet}
	</SectionHeader>
	<RoleFilter roles={roles.map(({ role, works }) => ({ role, count: works }))} bind:selected />

	<ListSection {list} failed="The songs did not load." empty="No songs">
		<ul class="overflow-hidden rounded-xl bg-card">
			{#each list.items as song (song.id)}
				<li class="flex items-center gap-3 px-3 py-2">
					<Thumb src={song.cover_thumbnail_url} name="" class="size-9 rounded-md" />
					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<SongTitle {song} />
							{#if song.variant}
								<!-- The icon marks the addition at the end of the line; hovering it names the addition. -->
								<span title={song.variant} class="ml-auto shrink-0 text-subtle">
									<PanelTop class="size-4" aria-label={song.variant} />
								</span>
							{/if}
							{#if song.import_state === 'stub'}<Badge>Stub</Badge>{/if}
						</div>
						{#if song.album}
							<div class="truncate text-xs text-subtle">{song.album}</div>
						{/if}
					</div>
					<div class="hidden max-w-64 flex-wrap justify-end gap-1 md:flex">
						{#each [...song.roles].sort() as role (role)}<Badge>{role}</Badge>{/each}
					</div>
					{#if song.genre}<span class="hidden text-xs text-muted-foreground lg:block"
							>{song.genre}</span
						>{/if}
					<span
						class="w-22 shrink-0 text-right font-mono text-xs whitespace-nowrap text-muted-foreground tabular-nums"
					>
						{formatRelease(song.release_date, song.release_date_precision) ?? ''}
					</span>
					<span
						class="w-14 shrink-0 text-right font-mono text-xs text-muted-foreground tabular-nums"
					>
						{song.view_count ? formatCount(song.view_count) : ''}
					</span>
				</li>
			{/each}
		</ul>
	</ListSection>
</section>
