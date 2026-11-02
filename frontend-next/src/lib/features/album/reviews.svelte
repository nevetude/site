<!-- A mockup: the reviews of the album, a card for a review: who, the score, the text. -->
<section class="space-y-3">
	<div class="space-y-3">
		{#each [1, 2, 3] as n (n)}
			<article class="space-y-3 rounded-lg bg-card p-4">
				<div class="flex items-center gap-3">
					<span class="size-8 shrink-0 rounded-full bg-accent"></span>
					<div class="h-2.5 w-28 rounded bg-accent"></div>
					<span class="ml-auto h-6 w-10 rounded-md bg-accent"></span>
				</div>
				<div class="space-y-1.5">
					<div class="h-2 w-full rounded bg-accent"></div>
					<div class="h-2 w-11/12 rounded bg-accent"></div>
					<div class="h-2 w-2/3 rounded bg-accent"></div>
				</div>
			</article>
		{/each}
	</div>
</section>
