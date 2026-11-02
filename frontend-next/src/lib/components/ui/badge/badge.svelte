<script lang="ts" module>
	const BASE =
		'gap-1 rounded-md px-2 py-0.5 text-xs font-medium [&>svg]:size-3! inline-flex w-fit shrink-0 items-center justify-center overflow-hidden whitespace-nowrap [&>svg]:pointer-events-none';

	const VARIANTS = {
		default: 'bg-accent text-foreground',
		destructive: 'bg-destructive/15 text-destructive',
		success: 'bg-success/15 text-success',
		warning: 'bg-warning/15 text-warning'
	} as const;

	export type BadgeVariant = keyof typeof VARIANTS;
</script>

<script lang="ts">
	import { cn, type WithElementRef } from '#lib/utils/cn.js';
	import type { HTMLAnchorAttributes } from 'svelte/elements';

	let {
		ref = $bindable(null),
		href,
		class: className,
		variant = 'default',
		children,
		...restProps
	}: WithElementRef<HTMLAnchorAttributes> & {
		variant?: BadgeVariant;
	} = $props();
</script>

<svelte:element
	this={href ? 'a' : 'span'}
	bind:this={ref}
	data-slot="badge"
	{href}
	class={cn(BASE, VARIANTS[variant], className)}
	{...restProps}
>
	{@render children?.()}
</svelte:element>
