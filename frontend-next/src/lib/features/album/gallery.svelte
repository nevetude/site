<script lang="ts">
	import ImageIcon from '@lucide/svelte/icons/image';

	// `tint` is the ground of the signs: the colour of the cover, as under the clips. `class` sets the gap between photos.
	let { tint, class: gap = 'gap-3' }: { tint: string | undefined; class?: string } = $props();
</script>

<!-- A mockup: photos of the album (booklet, vinyl, the studio), apart from the alternative covers above. One row of
     photos in 16:9, each with a sign under it in the style of the signs of the clips. -->
<section class="grid grid-cols-2 {gap}" aria-label="Gallery">
	{#each [1, 2] as n (n)}
		<figure>
			<div class="flex aspect-video items-center justify-center rounded-t-lg bg-card text-subtle">
				<ImageIcon class="size-5" />
			</div>
			<figcaption class="rounded-b-xl bg-card px-3 py-[9px]" style:background-color={tint}>
				<div class="text-xs text-foreground">Title</div>
				<div
					class="mt-0.5 flex h-4 items-baseline gap-2 text-[11px] leading-4 text-muted-foreground"
				>
					<span class="min-w-0 flex-1 truncate">Description</span>
					<span class="tabular-nums shrink-0">Year</span>
				</div>
			</figcaption>
		</figure>
	{/each}
</section>
