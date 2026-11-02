<script lang="ts">
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';

	// A button that stays pressed (a filter that is on or off), the same height and look as every other control.
	let {
		pressed = $bindable(false),
		class: className,
		children,
		...restProps
	}: Omit<HTMLButtonAttributes, 'type'> & { pressed?: boolean } = $props();
</script>

<button
	type="button"
	data-slot="toggle"
	aria-pressed={pressed}
	class={cn(
		"inline-flex h-8 items-center justify-center gap-2 rounded-md border border-transparent bg-accent px-3 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors outline-none hover:bg-foreground/15 hover:text-foreground focus-visible:border-focus disabled:pointer-events-none disabled:opacity-50 aria-pressed:bg-foreground/15 aria-pressed:text-foreground [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
		className
	)}
	onclick={() => (pressed = !pressed)}
	{...restProps}
>
	{@render children?.()}
</button>
