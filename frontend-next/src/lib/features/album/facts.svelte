<script lang="ts">
	import FactRow from '#lib/components/fact-row.svelte';

	// A mockup: what will come from another source is written as the name of its field.
	const ROWS = ['Recorded', 'Studio', 'Length', 'Format', 'Catalog number', 'Barcode'];
</script>

<!-- A mockup: the facts about the album that are not in the header (where and when it was made, the edition). -->
<section class="rounded-xl bg-card px-4 py-3" aria-label="Facts">
	<dl>
		{#each ROWS as label (label)}
			<FactRow {label}><span class="text-subtle">{label}</span></FactRow>
		{/each}
	</dl>
</section>
