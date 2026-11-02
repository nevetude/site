<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/cn.js';
	import { getSelect } from './select.svelte';

	let {
		value,
		label,
		class: className,
		children
	}: { value: string; label?: string; class?: string; children?: Snippet } = $props();

	const select = getSelect();
	const selected = $derived(select.value === value);
</script>

<div
	role="option"
	tabindex="-1"
	aria-selected={selected}
	data-slot="select-item"
	class={cn(
		'relative flex h-8 w-full cursor-default items-center gap-2 rounded-md pr-8 pl-3 text-sm whitespace-nowrap outline-hidden select-none focus:bg-accent',
		className
	)}
	onclick={() => select.pick(value)}
	onkeydown={(event) => {
		if (event.key !== 'Enter' && event.key !== ' ') return;
		event.preventDefault();
		select.pick(value);
	}}
	onpointermove={(event) => event.currentTarget.focus()}
>
	{#if children}{@render children()}{:else}{label || value}{/if}
	{#if selected}
		<CheckIcon class="pointer-events-none absolute right-3 size-4" />
	{/if}
</div>
