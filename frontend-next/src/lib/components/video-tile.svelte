<script lang="ts">
	import Pause from '@lucide/svelte/icons/pause';
	import Play from '@lucide/svelte/icons/play';
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/cn.js';

	// A clip as a picture with a play button over it, and a sign under it (`children`, none: just the picture). A picture
	// and a button, not a player: the browser caches the picture, and a page of many clips does not load a player for
	// each. The clip that is in the player (`current`) is dimmed; if the page tells that it sounds (`sounding`), bars
	// dance on its button and under the pointer they give way to the pause sign. `player`, if the page gives one, is drawn
	// in the place of the picture and its button (the clip is played where it stands). `tint` is the ground of the sign;
	// `ref` is the figure, for a page that moves its clips.
	type Props = {
		picture: string;
		label: string;
		current?: boolean;
		sounding?: boolean;
		tint?: string;
		caption?: string; // the classes of the sign: its padding
		large?: boolean; // the button as big as the play button of the cover panel (40px, icon 18px)
		player?: Snippet;
		ref?: HTMLElement | null;
		onplay: () => void;
		children?: Snippet;
	};

	let {
		picture,
		label,
		current = false,
		sounding,
		tint,
		caption = 'py-2',
		large = false,
		player,
		ref = $bindable(),
		onplay,
		children
	}: Props = $props();
</script>

<figure bind:this={ref}>
	{#if player}
		<div class="relative aspect-video w-full overflow-hidden rounded-t-lg bg-black">
			{@render player()}
		</div>
	{:else}
		<button
			type="button"
			aria-label={label}
			aria-current={current}
			class="group relative block aspect-video w-full overflow-hidden rounded-t-lg bg-black"
			onclick={onplay}
		>
			<img
				src={picture}
				alt=""
				loading="lazy"
				decoding="async"
				referrerpolicy="no-referrer"
				class={cn('size-full object-cover transition-opacity', current && 'opacity-40')}
			/>
			<span
				class={cn(
					'absolute inset-0 bg-black/0 transition-colors',
					!current && 'group-hover:bg-black/40'
				)}
				aria-hidden="true"
			></span>
			<span
				class="absolute top-1/2 left-1/2 flex {large
					? 'size-10'
					: 'size-9'} -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-black/60 transition-colors group-hover:bg-black"
			>
				{#if current && sounding}
					<Pause
						class="hidden {large
							? 'size-[18px]'
							: 'size-4'} fill-current text-white group-hover:block"
						aria-hidden="true"
					/>
					<span class="flex h-4 items-end gap-0.5 group-hover:hidden" aria-hidden="true">
						{#each [0, 1, 2] as bar (bar)}
							<span
								class="w-1 animate-equalizer rounded-full bg-white"
								style:animation-delay="{bar * -0.23}s"
								style:animation-duration="{0.9 + bar * 0.17}s"
							></span>
						{/each}
					</span>
				{:else}
					<Play
						class="{large ? 'size-[18px]' : 'size-4'} fill-current text-white"
						aria-hidden="true"
					/>
				{/if}
			</span>
		</button>
	{/if}
	{#if children}
		<figcaption class={cn('rounded-b-xl bg-card px-3', caption)} style:background-color={tint}>
			{@render children()}
		</figcaption>
	{/if}
</figure>
