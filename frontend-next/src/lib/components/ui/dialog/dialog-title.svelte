<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';

	let { class: className, children, ...restProps }: HTMLAttributes<HTMLHeadingElement> = $props();
</script>

<h2 data-slot="dialog-title" class={cn('leading-none font-medium', className)} {...restProps}>
	{@render children?.()}
</h2>
