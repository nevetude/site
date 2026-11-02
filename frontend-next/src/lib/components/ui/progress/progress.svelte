<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';

	let {
		class: className,
		max = 100,
		value,
		...restProps
	}: Omit<HTMLAttributes<HTMLDivElement>, 'role'> & { max?: number; value: number } = $props();
</script>

<div
	role="progressbar"
	aria-valuemin={0}
	aria-valuemax={max}
	aria-valuenow={value}
	data-slot="progress"
	class={cn(
		'relative flex h-1.5 w-full items-center overflow-x-hidden rounded-full bg-muted',
		className
	)}
	{...restProps}
>
	<div
		data-slot="progress-indicator"
		class="size-full flex-1 bg-primary transition-all"
		style="transform: translateX(-{100 - (100 * value) / max}%)"
	></div>
</div>
