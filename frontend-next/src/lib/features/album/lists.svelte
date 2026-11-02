<script lang="ts">
	import ListMusic from '@lucide/svelte/icons/list-music';
</script>

<!-- A mockup: the lists (collections, playlists) this album is in, one row for a list. -->
<section class="space-y-3">
	<ul class="space-y-2">
		{#each [1, 2, 3] as n (n)}
			<li class="flex items-center gap-3 rounded-lg bg-card p-2.5">
				<span
					class="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent text-subtle"
				>
					<ListMusic class="size-5" />
				</span>
				<div class="min-w-0 flex-1 space-y-1.5">
					<div class="h-2.5 w-3/4 rounded bg-accent"></div>
					<div class="h-2 w-1/2 rounded bg-accent"></div>
				</div>
				<div class="h-2.5 w-8 shrink-0 rounded bg-accent"></div>
			</li>
		{/each}
	</ul>
</section>
