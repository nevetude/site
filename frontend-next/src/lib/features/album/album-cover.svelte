<script lang="ts">
	import CoverPlaceholder from '#lib/components/cover-placeholder.svelte';
	import ExplicitEye from '#lib/components/explicit-eye.svelte';
	import type { Cover } from '#lib/utils/albums.js';

	// Only thumbnails are drawn here; the full pictures are in the overlay (`CoverViewer`).
	// A cover that is marked `explicit` is blurred a little, with a small grey eye over it, until the cover is pressed
	// once; the next press opens the covers. The covers behind the main one follow it.
	type Props = { covers: Cover[]; onopen: () => void };

	let { covers, onopen }: Props = $props();

	let shown = $state(false);
	const empty = $derived(!!covers[0]?.placeholder); // the album has no cover: a grey box, and nothing to open
	const hidden = $derived(!shown && !empty && !!covers[0]?.explicit);
	const blurred = (cover: Cover | undefined) => !shown && !!cover?.explicit;

	// Up to two more covers lie behind the main one, fanned out like photos: the second peeks out on the left, the third on
	// the right, only a little; the pointer pulls them out a bit more.
	const behind = $derived(
		covers
			.slice(1)
			.filter((cover) => !cover.placeholder)
			.slice(0, 2)
	);
	const FAN = [
		'-translate-x-[6%] -rotate-[3deg] group-hover:-translate-x-[12%] group-hover:-rotate-[5deg] group-focus-visible:-translate-x-[12%]',
		'translate-x-[6%] rotate-[3deg] group-hover:translate-x-[12%] group-hover:rotate-[5deg] group-focus-visible:translate-x-[12%]'
	];
</script>

<div class="flex justify-center">
	<button
		type="button"
		class="group relative size-[12.25rem] cursor-pointer rounded-lg min-[1000px]:size-[214px]"
		aria-label={empty ? 'No cover' : hidden ? 'Explicit cover: show' : 'View all covers'}
		disabled={empty}
		onclick={() => (hidden ? (shown = true) : onopen())}
	>
		{#each behind as cover, i (cover.url)}
			<img
				src={cover.thumb}
				alt=""
				loading="lazy"
				decoding="async"
				referrerpolicy="no-referrer"
				class="absolute inset-0 size-full rounded-lg object-cover opacity-80 brightness-75 transition-[transform,filter] duration-200 ease-out shadow-[0_6px_16px_rgba(0,0,0,0.4)] {blurred(
					cover
				)
					? 'scale-110 blur-xs'
					: ''} {FAN[i]}"
			/>
		{/each}
		{#if covers[0]}
			<span
				class="relative block size-full overflow-hidden rounded-lg shadow-[0_0_30px_6px_rgba(0,0,0,0.65)]"
			>
				{#if empty}
					<CoverPlaceholder class="size-10" />
				{:else}
					<img
						src={covers[0].thumb}
						alt=""
						decoding="async"
						referrerpolicy="no-referrer"
						class="block size-full bg-black/20 object-cover transition-[filter,transform] duration-200 {hidden
							? 'scale-110 blur-xs'
							: ''}"
					/>
				{/if}
				{#if hidden}
					<ExplicitEye class="group-hover:text-white/90 group-focus-visible:text-white/90" />
				{/if}
			</span>
		{/if}
	</button>
</div>
