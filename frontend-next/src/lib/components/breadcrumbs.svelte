<script lang="ts">
	import type { Snippet } from 'svelte';
	import { resolve } from '$app/paths';
	import * as Breadcrumb from '#lib/components/ui/breadcrumb/index.js';

	// The way to the page, from the home page: every part but the last one leads back. `href` of a part is already
	// resolved by the page that knows the route (the lint rule cannot see that through a prop).
	type Crumb = { label: string; href?: string };

	// `end`: what stands at the right edge of the line.
	let { trail, end }: { trail: Crumb[]; end?: Snippet } = $props();
</script>

<!-- Out of the flow, in the 1.75rem between the header and the first block of the page (`main` is positioned and has that
     much room at the top): the block stands at the same height whether the page has breadcrumbs or not. -->
<Breadcrumb.Root class="absolute inset-x-6 top-0 flex h-8 items-center">
	<Breadcrumb.List>
		<Breadcrumb.Item><Breadcrumb.Link href={resolve('/')}>Home</Breadcrumb.Link></Breadcrumb.Item>
		{#each trail as crumb, i (i)}
			<Breadcrumb.Separator />
			<Breadcrumb.Item>
				{#if i < trail.length - 1 && crumb.href}
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<Breadcrumb.Link href={crumb.href}>{crumb.label}</Breadcrumb.Link>
				{:else}
					<Breadcrumb.Page>{crumb.label}</Breadcrumb.Page>
				{/if}
			</Breadcrumb.Item>
		{/each}
	</Breadcrumb.List>
	{#if end}<div class="ml-auto">{@render end()}</div>{/if}
</Breadcrumb.Root>
