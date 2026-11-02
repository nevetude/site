<script lang="ts">
	import type { Snippet } from 'svelte';
	import ReleaseControls from '#lib/components/release-controls.svelte';

	// The coloured panel at the top left of a detail page: the cover (or the portrait) in the middle and the panel of
	// buttons under it. It is as high as the first row of the page and 2.625rem more, which the block under it (the
	// tracklist, the facts) lies over; so the picture is centred in the part that stays visible. `label` names the panel
	// of buttons for a screen reader; `tint` is the colour of the cover.
	type Props = {
		label?: string;
		tint?: string;
		back?: Snippet;
		controls?: boolean; // false: no buttons under the picture, which then stands in the middle
		children: Snippet;
	};

	let { label, tint, back, controls = true, children }: Props = $props();
</script>

<section
	class="relative aspect-square h-full overflow-hidden rounded-xl bg-card min-[1000px]:aspect-auto min-[1000px]:min-h-[calc(360px+2.625rem)]"
	style:background-color={tint}
>
	{@render back?.()}
	<div class="absolute inset-x-0 top-0 flex h-full flex-col min-[1000px]:h-[calc(100%-2.625rem)]">
		{#if controls}
			<div class="flex-[57.5]"></div>
			{@render children()}
			<div class="flex-[25]"></div>
			<ReleaseControls {label} />
			<div class="flex-[16.5]"></div>
		{:else}
			<div class="flex-1"></div>
			{@render children()}
			<div class="flex-1"></div>
		{/if}
	</div>
</section>
