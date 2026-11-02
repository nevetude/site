<script lang="ts">
	import '../app.css';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { session } from '#lib/utils/session.svelte.js';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	const links = [{ href: '/import', label: 'Import' }] as const;

	void session.load();
</script>

<svelte:head>
	<title>Music</title>
</svelte:head>

<header class="sticky top-0 z-20 border-b bg-background/85 backdrop-blur">
	<div class="mx-auto flex h-12 max-w-page items-center gap-8 px-6">
		<a href={resolve('/')} class="font-semibold tracking-tight">Music</a>
		<nav class="flex gap-5 text-sm">
			{#each links as link (link.href)}
				<a
					href={resolve(link.href)}
					aria-current={page.url.pathname.startsWith(link.href) ? 'page' : undefined}
					class="text-subtle hover:text-foreground aria-[current=page]:text-foreground"
				>
					{link.label}
				</a>
			{/each}
		</nav>
	</div>
</header>

<!-- Every page starts 1.75rem under the header: its first block (the cover, the form), or the heading if there is no
     cover. The breadcrumbs stand in that room (`Breadcrumbs`), so a page with them and a page without them start at
     the same height. -->
<main class="relative mx-auto max-w-page px-6 pt-8 pb-8">
	{@render children()}
</main>
