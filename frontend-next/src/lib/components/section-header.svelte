<script lang="ts">
	import type { Snippet } from 'svelte';

	// The head of a block of the page: its name, how many there are, and the controls at the right end.
	type Props = { title: string; count?: number; actions?: Snippet };

	let { title, count, actions }: Props = $props();
</script>

<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
	<!-- The name and the count stand on one baseline, whatever their sizes are. -->
	<div class="flex items-baseline gap-4">
		<h2 class="text-base font-semibold">{title}</h2>
		{#if count !== undefined}<span class="text-xs text-subtle tabular-nums">{count}</span>{/if}
	</div>
	{#if actions}<div class="ml-auto">{@render actions()}</div>{/if}
</header>
