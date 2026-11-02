<script lang="ts">
	import { fade } from 'svelte/transition';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import type { YoutubePlayer } from '#lib/utils/youtube-player.svelte.js';

	// The `<iframe>` of the YouTube player of a page. The buttons of the player have one size whatever the size of the
	// frame: it is laid out in a frame 1/s times the box and shown at s times, so that its interface is s times as big as
	// it is (`scale` is s: 0.864 on the album page, frame 115.741%; the smaller it is, the smaller the buttons). On the
	// whole screen it is drawn as it is. The box that holds it is `relative` and cuts what sticks out.
	let {
		player,
		title,
		scale = 0.864
	}: { player: YoutubePlayer; title?: string; scale?: number } = $props();
</script>

<iframe
	bind:this={player.frame}
	onload={player.listen}
	src={player.embed}
	{title}
	allow="autoplay; fullscreen"
	referrerpolicy="strict-origin-when-cross-origin"
	style:--s={scale}
	class="absolute top-0 left-0 size-[calc(100%/var(--s))] origin-top-left scale-(--s) transition-opacity duration-300 ease-out [&:fullscreen]:size-full [&:fullscreen]:scale-100 {player.hidden
		? 'opacity-0'
		: ''}"
></iframe>
<!-- The player is hidden (black) until the clip has begun: a spinner turns over it meanwhile. -->
{#if player.hidden}
	<div
		class="pointer-events-none absolute inset-0 flex items-center justify-center"
		transition:fade={{ duration: 200 }}
	>
		<Spinner class="size-10 stroke-3 text-white" aria-label="The clip is loading" />
	</div>
{/if}
