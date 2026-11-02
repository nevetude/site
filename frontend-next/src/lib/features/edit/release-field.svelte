<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import { api, type ReleaseRef } from '#lib/api/client.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import SearchPick from '#lib/features/edit/search-pick.svelte';
	import { formatRelease } from '#lib/utils/format.js';

	// A release (an album or a song) of an artist: the chip of the one that is chosen, with a cross to take it away,
	// or, while none is, a search among the releases of the artist (`artistId`).
	type Props = {
		artistId: number;
		release: ReleaseRef | null;
		label: string;
		placeholder?: string;
		removable?: boolean; // the chip has a cross (a list that has its own cross for the row does without)
	};

	let {
		artistId,
		release = $bindable(),
		label,
		placeholder = 'a release',
		removable = true
	}: Props = $props();

	async function search(q: string) {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/releases', {
			params: { path: { artist_id: artistId }, query: { q } }
		});
		return data ?? [];
	}
</script>

{#if release}
	<span class="inline-flex max-w-full items-center gap-1.5 rounded-md bg-muted px-2 py-1 text-xs">
		<Badge>{release.kind}</Badge>
		<span class="truncate">{release.name}</span>
		{#if release.release_date}
			<span class="text-subtle tabular-nums"
				>{formatRelease(release.release_date, release.release_date_precision)}</span
			>
		{/if}
		{#if removable}
			<Button
				variant="close"
				size="icon"
				class="size-5"
				aria-label="Take away {release.name}"
				onclick={() => (release = null)}
			>
				<X />
			</Button>
		{/if}
	</span>
{:else}
	<SearchPick {label} {placeholder} {search} onpick={(one) => (release = one)}>
		{#snippet row(one: ReleaseRef)}
			<Badge>{one.kind}</Badge>
			<span class="min-w-0 flex-1 truncate text-left text-sm">
				{one.name}{#if one.variant}<span class="ml-1.5 text-muted-foreground">{one.variant}</span
					>{/if}
			</span>
			<span class="text-xs text-subtle tabular-nums"
				>{formatRelease(one.release_date, one.release_date_precision) ?? ''}</span
			>
		{/snippet}
	</SearchPick>
{/if}
