<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import type { PagedList } from '#lib/utils/paged.svelte.js';

	// What a list read from a paged endpoint shows besides its items: the failure, the empty state, and the button that
	// reads the next page (`more` false: the whole list is loaded at once, there is no button).
	type Props = {
		list: PagedList<T>;
		failed: string;
		empty: string;
		more?: boolean;
		children: Snippet;
	};

	let { list, failed, empty, more = true, children }: Props = $props();
</script>

{#if list.failed}
	<p class="text-sm text-destructive">{failed}</p>
{:else if !list.loading && !list.items.length}
	<p class="rounded-xl bg-card p-6 text-center text-sm text-subtle">{empty}</p>
{:else}
	{@render children()}
	{#if more && list.items.length < list.total}
		<div class="flex justify-center pt-1">
			<Button class="text-sm" disabled={list.loading} onclick={() => list.more()}>
				{#if list.loading}<Spinner />{/if}
				Show more ({list.total - list.items.length})
			</Button>
		</div>
	{/if}
{/if}
