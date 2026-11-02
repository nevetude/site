<script lang="ts">
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';
	import { getSelect } from './select.svelte';

	// The button that opens the list. `chevron` false: a button that is only a word (the sort field), with no arrow
	// that could be taken for the direction of the sort.
	let {
		class: className,
		children,
		size = 'default',
		chevron = true,
		...restProps
	}: Omit<HTMLButtonAttributes, 'type'> & { size?: 'sm' | 'default'; chevron?: boolean } = $props();

	const select = getSelect();

	function onkeydown(event: KeyboardEvent) {
		if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
		event.preventDefault();
		select.open = true;
	}
</script>

<button
	bind:this={select.trigger}
	type="button"
	data-slot="select-trigger"
	data-size={size}
	aria-haspopup="listbox"
	aria-expanded={select.open}
	disabled={select.disabled}
	class={cn(
		"flex h-8 w-fit items-center justify-between gap-2 rounded-md border border-transparent bg-accent pr-2 pl-3 text-sm whitespace-nowrap transition-colors outline-none hover:bg-foreground/15 focus-visible:border-focus disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive [&_svg:not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:shrink-0",
		className
	)}
	onclick={() => (select.open = !select.open)}
	{onkeydown}
	{...restProps}
>
	<span class="line-clamp-1 flex items-center gap-2">{@render children?.()}</span>
	{#if chevron}<ChevronDownIcon class="pointer-events-none size-4 text-muted-foreground" />{/if}
</button>
