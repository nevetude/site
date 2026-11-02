<script lang="ts">
	import { cn, type WithElementRef } from '#lib/utils/cn.js';
	import type { HTMLAttributes } from 'svelte/elements';

	let {
		ref = $bindable(null),
		class: className,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLHeadingElement>> = $props();
</script>

<!-- A real heading (shadcn draws a div): the title of a card names its block for a screen reader and for the tests. -->
<h2
	bind:this={ref}
	data-slot="card-title"
	class={cn('text-base leading-normal font-medium group-data-[size=sm]/card:text-sm', className)}
	{...restProps}
>
	{@render children?.()}
</h2>
