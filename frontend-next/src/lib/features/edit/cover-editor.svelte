<script lang="ts">
	import CoverPlaceholder from '#lib/components/cover-placeholder.svelte';
	import ExplicitEye from '#lib/components/explicit-eye.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import type { Cover } from '#lib/utils/albums.js';

	// Changes the main cover (or the photo): one of the covers that are known, or the address of a picture. The colours
	// of the card come from Genius's cover, so a picture of another address has none.
	export type NewCover = {
		url: string;
		thumbnail: string;
		primary: string | null;
		secondary: string | null;
	};
	/** What a page holds for its cover: the cover that was chosen, whether to put it back to Genius, and whether it was changed. */
	export type CoverDraft = {
		cover: NewCover | null;
		reset: { cover: boolean };
		edited(field: string): boolean;
	};
	type Props = {
		open: boolean;
		known: Cover[];
		onpick: (cover: NewCover) => void;
	};

	let { open = $bindable(), known, onpick }: Props = $props();

	let address = $state('');

	function choose(url: string, thumbnail: string) {
		onpick({ url, thumbnail, primary: null, secondary: null });
		open = false;
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Cover</Dialog.Title>
			<Dialog.Description
				>Pick a cover that is known, or give the address of a picture.</Dialog.Description
			>
		</Dialog.Header>
		{#if known.length}
			<ul class="grid grid-cols-4 gap-2" aria-label="Known covers">
				{#each known as cover (cover.url)}
					<li>
						<button
							type="button"
							class="group/cover block aspect-square w-full overflow-hidden rounded-lg hover:opacity-80"
							aria-label="Use this cover"
							onclick={() => choose(cover.url, cover.thumb)}
						>
							<span class="relative block size-full">
								{#if cover.placeholder}
									<CoverPlaceholder />
								{:else}
									<img
										src={cover.thumb}
										alt=""
										loading="lazy"
										referrerpolicy="no-referrer"
										class="size-full object-cover {cover.explicit ? 'scale-110 blur-xs' : ''}"
									/>
									{#if cover.explicit}<ExplicitEye class="group-hover/cover:text-white/90" />{/if}
								{/if}
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
		<form
			class="flex gap-2"
			onsubmit={(event) => {
				event.preventDefault();
				if (address.trim()) choose(address.trim(), address.trim());
			}}
		>
			<Input
				bind:value={address}
				aria-label="Address of the picture"
				placeholder="https://…"
				class="border-transparent"
			/>
			<Button type="submit" disabled={!address.trim()}>Use</Button>
		</form>
	</Dialog.Content>
</Dialog.Root>
