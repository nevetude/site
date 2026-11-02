<script lang="ts">
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import ResetButton from '#lib/features/edit/reset-button.svelte';

	// The description as a text of paragraphs. What Genius wrote has links and marks: a text written here has none, and
	// replaces it until it is put back.
	type Props = { value: string; edited: boolean; reset: boolean };

	let { value = $bindable(), edited, reset = $bindable() }: Props = $props();
</script>

<div class="space-y-2 rounded-xl bg-card p-4">
	<div class="flex items-center justify-between">
		<span class="text-[13px] text-subtle">Description</span>
		<ResetButton {edited} bind:reset label="description" />
	</div>
	<Textarea
		bind:value
		rows={10}
		aria-label="Description"
		disabled={reset}
		class="border-transparent leading-relaxed"
	/>
</div>
