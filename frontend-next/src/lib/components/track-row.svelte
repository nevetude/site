<script lang="ts">
	import type { Snippet } from 'svelte';
	import CommaList from '#lib/components/comma-list.svelte';
	import ExplicitMark from '#lib/components/explicit-mark.svelte';
	import Thumb from '#lib/components/thumb.svelte';
	import { cn } from '#lib/utils/cn.js';
	import { formatCount } from '#lib/utils/format.js';

	// One song in a list, a link to its page: its picture, the title with what stands after it (`inline`: the
	// featured artists, a stub mark), a second line (`sub`: the album, the artists), the producers and the views at the
	// right end. `lead` is a column before the picture (the number on an album). Everything written stands on one line:
	// what does not fit is cut with "…". Every row is 40px high, with or without a second line: two lines fit in it,
	// so a row never grows. The producers, the mark and the views are centred on the whole row, not on the
	// line of the title.
	type Props = {
		href: string;
		thumb: string | null;
		title: string;
		variant?: string | null;
		lead?: Snippet;
		inline?: Snippet;
		sub?: Snippet;
		producers?: { names: string[]; tinted?: boolean[] };
		views?: number | null;
		viewsTitle?: string;
		explicit?: boolean;
		class?: string;
	};

	let {
		href,
		thumb,
		title,
		variant,
		lead,
		inline,
		sub,
		producers,
		views,
		viewsTitle,
		explicit = false,
		class: className
	}: Props = $props();
</script>

<!-- The address is made by the page that knows the route (the lint rule cannot see that through a prop). -->
<!-- eslint-disable svelte/no-navigation-without-resolve -->
<a
	{href}
	class={cn(
		'grid h-[40px] items-center gap-2 rounded-lg px-[12px] hover:bg-black/20',
		// The lead (the number on an album) is the whole 28px from the edge to the picture, with no gap after it.
		lead
			? 'grid-cols-[28px_1.75rem_minmax(0,1fr)] gap-x-0 pl-0'
			: 'grid-cols-[1.75rem_minmax(0,1fr)]',
		className
	)}
>
	{@render lead?.()}
	<Thumb src={thumb} name="" class="size-8 rounded-md" />
	<div class={cn('flex min-w-0 items-center gap-2', lead && 'pl-2')}>
		<div class="flex min-w-0 flex-1 flex-col">
			<div class="flex min-w-0 items-baseline gap-1.5">
				<span class="truncate text-sm leading-snug">
					{title}{#if variant}<span class="ml-1.5 text-muted-foreground">{variant}</span>{/if}
				</span>
				{@render inline?.()}
			</div>
			{#if sub}
				<div class="mt-0.5 truncate text-xs leading-snug text-muted-foreground empty:hidden">
					{@render sub()}
				</div>
			{/if}
		</div>
		{#if producers?.names.length}
			<span
				class="max-w-25 truncate text-right text-[12px] text-muted-foreground"
				title={producers.names.join(', ')}
			>
				<CommaList items={producers.names} wrap={false} tinted={producers.tinted} />
			</span>
		{/if}
		{#if views !== undefined || explicit}
			<span class="flex shrink-0 flex-row-reverse items-center gap-1">
				<!-- At least 14px, with or without a count: a short count keeps the mark before it in place, a long one moves it. -->
				<span
					class="min-w-[14px] text-right text-[10px] text-muted-foreground tabular-nums"
					title={viewsTitle}
				>
					{views ? formatCount(views) : ''}
				</span>
				{#if explicit}<ExplicitMark class="size-[10px] text-muted-foreground" />{/if}
			</span>
		{/if}
	</div>
</a>
