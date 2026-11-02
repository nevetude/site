<script lang="ts">
	import type { Snippet } from 'svelte';
	import ExtLink from '#lib/components/ext-link.svelte';

	// The head of a detail page: the title (one line, cut with "…" when long; the whole of it is in the tooltip) with
	// what goes after it (`after`: the variant, a mark), and under it a line of artists (`children`). The title leads to
	// the entity on Genius for now.
	type Props = {
		title: string;
		tooltip?: string;
		genius?: string | null;
		after?: Snippet;
		edit?: Snippet; // the fields of the title in the edit mode, in the place of the title
		children?: Snippet;
	};

	let { title, tooltip = title, genius, after, edit, children }: Props = $props();
</script>

<div class="space-y-2">
	{#if edit}
		<div class="space-y-1.5">{@render edit()}</div>
	{:else}
		<h1 title={tooltip} class="truncate text-[1.2rem] leading-tight font-bold">
			{#if genius}
				<ExtLink href={genius} title="Open on Genius">{title}</ExtLink>
			{:else}{title}{/if}
			{@render after?.()}
		</h1>
	{/if}
	<p class="truncate text-lg font-medium empty:hidden">{@render children?.()}</p>
</div>
