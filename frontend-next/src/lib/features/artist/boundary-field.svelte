<script lang="ts">
	import { Button } from '#lib/components/ui/button/index.js';
	import type { DraftBoundary } from '#lib/features/artist/artist-draft.svelte.js';
	import PartialDateInput from '#lib/features/edit/partial-date-input.svelte';
	import ReleaseField from '#lib/features/edit/release-field.svelte';

	// One end of the time in a group: a date (a year is enough), or a release of the group, whose date it follows.
	type Props = { boundary: DraftBoundary; artistId: number; label: string };

	let { boundary = $bindable(), artistId, label }: Props = $props();

	let picking = $state(false);
</script>

<div class="flex flex-wrap items-center gap-1">
	{#if boundary.release}
		<ReleaseField {artistId} bind:release={boundary.release} {label} />
	{:else}
		<PartialDateInput
			bind:value={boundary.date}
			{label}
			placeholder="year"
			class="h-7 w-24 text-xs"
		/>
		{#if picking}
			<ReleaseField
				{artistId}
				bind:release={boundary.release}
				label="Release for {label}"
				placeholder="a release"
			/>
		{/if}
		<Button
			variant="ghost"
			class="text-muted-foreground"
			title="Tie it to a release: the date follows the release"
			onclick={() => (picking = !picking)}
		>
			{picking ? 'date' : 'release'}
		</Button>
	{/if}
</div>
