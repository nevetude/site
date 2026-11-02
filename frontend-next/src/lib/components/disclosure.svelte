<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import type { Snippet } from 'svelte';

	// A block with a title that opens and closes. `onopen` is called each time it opens (the raw response is read then).
	type Props = { title: string; open?: boolean; onopen?: () => void; children: Snippet };

	let { title, open = $bindable(false), onopen, children }: Props = $props();

	function toggle() {
		open = !open;
		if (open) onopen?.();
	}
</script>

<button
	type="button"
	aria-expanded={open}
	class="flex w-full items-center gap-2 px-5 py-3 text-sm text-muted-foreground hover:text-foreground"
	onclick={toggle}
>
	<ChevronRight class="size-4 transition-transform {open ? 'rotate-90' : ''}" />
	{title}
</button>
{#if open}<div class="p-5">{@render children()}</div>{/if}
