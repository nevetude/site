<script lang="ts">
	import type { Snippet } from 'svelte';

	// A card with a bite out of the top right corner (`.notched-right`, `app.css`) and a small mark in the bite
	// (`corner`). `bite` is the width of the bite (a CSS length), its height stays 27px. `tint` is the colour of the card.
	type Props = {
		tint?: string;
		corner: Snippet;
		bite: string;
		children: Snippet;
	};

	let { tint, corner, bite, children }: Props = $props();
</script>

<div class="relative" style:--notch-bg={tint ?? 'var(--card)'} style:--bite-w={bite}>
	<div
		class="absolute top-0 right-0 z-10 flex h-[27px] items-center justify-center"
		style:width={bite}
	>
		{@render corner()}
	</div>
	<section class="notched-right relative rounded-xl bg-(--notch-bg) pt-3 pb-1">
		{@render children()}
	</section>
</div>
