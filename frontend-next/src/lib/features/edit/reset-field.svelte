<script lang="ts">
	import type { Snippet } from 'svelte';
	import ResetButton from '#lib/features/edit/reset-button.svelte';

	// A field of the edit mode with the button beside it that puts it back to what Genius has.
	type Props = { edited: boolean; reset: boolean; label: string; children: Snippet };

	let { edited, reset = $bindable(), label, children }: Props = $props();
</script>

<div class="flex items-center gap-1">
	{@render children()}
	<ResetButton {edited} bind:reset {label} />
</div>
