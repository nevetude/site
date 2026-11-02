<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import type { HTMLInputAttributes } from 'svelte/elements';
	import { cn } from '#lib/utils/cn.js';

	// A native checkbox drawn by the site: filled, no edge, the mark appears when it is on. The label around it (or
	// `aria-label`) names it; the browser takes care of the keyboard and of the form.
	let {
		checked = $bindable(false),
		class: className,
		...restProps
	}: Omit<HTMLInputAttributes, 'type' | 'checked'> & { checked?: boolean } = $props();
</script>

<span class="relative inline-flex size-4 shrink-0">
	<input
		type="checkbox"
		data-slot="checkbox"
		bind:checked
		class={cn(
			'peer size-4 cursor-pointer appearance-none rounded-[4px] border border-transparent bg-input transition-colors outline-none checked:bg-primary focus-visible:border-focus aria-invalid:border-destructive disabled:cursor-not-allowed disabled:opacity-50',
			className
		)}
		{...restProps}
	/>
	<CheckIcon
		class="pointer-events-none absolute inset-0 m-auto hidden size-3.5 text-primary-foreground peer-checked:block"
	/>
</span>
