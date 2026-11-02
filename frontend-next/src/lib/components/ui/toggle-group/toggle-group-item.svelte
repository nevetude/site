<script lang="ts">
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';
	import { getToggleGroup } from './toggle-group.svelte';

	let {
		value,
		class: className,
		children,
		...restProps
	}: Omit<HTMLButtonAttributes, 'type' | 'value'> & { value: string } = $props();

	const group = getToggleGroup();
</script>

<button
	type="button"
	data-slot="toggle-group-item"
	aria-pressed={group.value === value}
	class={cn(
		"inline-flex h-full w-8 shrink-0 items-center justify-center text-foreground/60 transition-colors outline-none hover:bg-foreground/10 hover:text-foreground focus-visible:z-10 focus-visible:shadow-[inset_0_0_0_1px_var(--color-focus)] aria-pressed:bg-foreground/15 aria-pressed:text-foreground [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
		className
	)}
	onclick={() => group.pick(value)}
	{...restProps}
>
	{@render children?.()}
</button>
