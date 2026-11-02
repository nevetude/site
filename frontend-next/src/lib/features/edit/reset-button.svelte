<script lang="ts">
	import Undo2 from '@lucide/svelte/icons/undo-2';
	import { Button } from '#lib/components/ui/button/index.js';

	// Beside a field that was set by hand: marks it to go back to what Genius has when the page is saved (the value of
	// Genius is not known to the page, so it comes with the save). Pressed again, it keeps the value.
	type Props = { edited: boolean; reset: boolean; label: string };

	let { edited, reset = $bindable(), label }: Props = $props();
</script>

{#if edited}
	<Button
		type="button"
		variant="ghost"
		size="icon"
		aria-pressed={reset}
		aria-label="{reset ? 'Keep my value of' : 'Back to Genius:'} {label}"
		title={reset ? 'Keep my value' : 'Back to Genius when saved'}
		class={reset ? 'text-warning' : 'text-subtle'}
		onclick={() => (reset = !reset)}
	>
		<Undo2 />
	</Button>
{/if}
