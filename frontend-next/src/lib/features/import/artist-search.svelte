<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Search from '@lucide/svelte/icons/search';
	import { api, type ArtistHit } from '#lib/api/client.js';
	import Thumb from '#lib/components/thumb.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { openPopover } from '#lib/utils/popover.js';

	// Looks an artist up on Genius by name and lists the hits; `onpick` is called for the one that is pressed (the
	// results stay open, so several can be picked), `chosen` are the ids that are marked as picked already. The results
	// lie over the page (nothing moves) and close with Escape, with a press anywhere else, or by a new search.
	type Props = {
		label: string; // for a screen reader: the field has only a short grey hint
		chosen?: number[];
		onpick: (hit: ArtistHit) => void;
	};

	let { label, chosen = [], onpick }: Props = $props();

	let query = $state('');
	let hits = $state<ArtistHit[] | null>(null);
	let searching = $state(false);
	let searchError = $state('');
	let anchor = $state<HTMLElement>();
	let list = $state<HTMLElement>();
	const open = $derived(hits !== null); // not `hits` itself: a new answer must not open the list again

	$effect(() => {
		if (!open || !list || !anchor) return;
		return openPopover(list, anchor, () => (hits = null));
	});

	const dbLabel = { stub: 'Stub', full: 'In library' } as const;

	async function search(event: SubmitEvent) {
		event.preventDefault();
		if (!query.trim()) return;
		searching = true;
		searchError = '';
		try {
			const { data } = await api.GET('/api/v1/genius/search/artists', {
				params: { query: { q: query.trim() } }
			});
			hits = data ?? null;
			if (!data) searchError = 'The search failed: Genius did not answer';
		} catch {
			searchError = 'The search failed: the backend is not running';
		} finally {
			searching = false;
		}
	}
</script>

<form bind:this={anchor} class="flex gap-2" onsubmit={search}>
	<Input bind:value={query} aria-label={label} placeholder="name" />
	<Button type="submit" disabled={searching}>
		{#if searching}<Spinner />{:else}<Search />{/if}
		Search
	</Button>
</form>
{#if searchError}<p class="text-sm text-destructive">{searchError}</p>{/if}

<ul bind:this={list} popover="manual" aria-label="Found" class="popup">
	{#each hits ?? [] as hit (hit.genius_id)}
		{@const picked = chosen.includes(hit.genius_id)}
		<li>
			<Button
				variant="ghost"
				aria-pressed={picked}
				class="h-auto w-full justify-start gap-3 px-3 py-2 font-normal aria-pressed:bg-accent"
				onclick={() => onpick(hit)}
			>
				<Thumb src={hit.image_url} name={hit.name} class="size-8 rounded-full" />
				<span class="min-w-0 flex-1 truncate text-left">{hit.name}</span>
				<span class="text-xs text-subtle tabular-nums">{hit.genius_id}</span>
				{#if hit.db_state}<Badge variant="success">{dbLabel[hit.db_state]}</Badge>{/if}
				{#if picked}<Check />{/if}
			</Button>
		</li>
	{:else}
		<li class="p-4 text-center text-sm text-muted-foreground">Nothing found</li>
	{/each}
</ul>
