<script lang="ts">
	import BadgeCheck from '@lucide/svelte/icons/badge-check';
	import CoverPanel from '#lib/components/cover-panel.svelte';
	import Thumb from '#lib/components/thumb.svelte';
	import type { ArtistDraft } from '#lib/features/artist/artist-draft.svelte.js';
	import CoverViewer from '#lib/features/album/cover-viewer.svelte';
	import CoverEditor from '#lib/features/edit/cover-editor.svelte';
	import ResetButton from '#lib/features/edit/reset-button.svelte';
	import ImageUp from '@lucide/svelte/icons/image-up';

	// `draft`: the page is being edited, and the photo can be changed (by the address of a picture).
	type Props = {
		src: string | null;
		name: string;
		verified: boolean | null;
		draft?: ArtistDraft | null;
	};

	let { src, name, verified, draft = $bindable(null) }: Props = $props();

	const shown = $derived(draft?.cover?.url ?? src);
	let viewing = $state(false); // the photo is open in the overlay of the covers
	let index = $state(0);
	let changing = $state(false); // the window to choose another photo
</script>

<!-- The same panel as the cover of an album, with a round portrait. The portrait is blurred behind itself into a faint
     field, so the round shape stands on its own colour and not on the grey of the card; the badge of a verified artist
     sits on the rim of the circle, where a round picture has room for it. -->
<CoverPanel label="Artist" controls={!draft}>
	{#snippet back()}
		{#if draft?.edited('cover_url')}
			<div class="absolute top-2 left-2 z-10">
				<ResetButton edited bind:reset={draft.reset.cover} label="photo" />
			</div>
		{/if}
		{#if shown}
			<img
				src={shown}
				alt=""
				aria-hidden="true"
				referrerpolicy="no-referrer"
				class="absolute inset-0 size-full scale-150 object-cover opacity-30 blur-3xl"
			/>
		{/if}
	{/snippet}
	<div class="flex justify-center">
		<div class="relative size-56 min-[1000px]:size-[214px]">
			{#if draft}
				<!-- In the edit mode the photo is dimmed and a click on it opens the choice of another one. -->
				<button
					type="button"
					aria-label="Change the photo"
					disabled={draft.reset.cover}
					class="group relative block size-full cursor-pointer overflow-hidden rounded-full disabled:cursor-default"
					onclick={() => (changing = true)}
				>
					<Thumb src={shown} {name} class="size-full rounded-full shadow-2xl" />
					<span
						class="absolute inset-0 flex items-center justify-center rounded-full bg-black/55 text-white transition-colors group-hover:bg-black/65"
					>
						<ImageUp class="size-9" />
					</span>
				</button>
			{:else if shown}
				<button
					type="button"
					aria-label="View the photo"
					class="block size-full cursor-pointer rounded-full"
					onclick={() => (viewing = true)}
				>
					<Thumb src={shown} {name} class="size-full rounded-full shadow-2xl" />
				</button>
			{:else}
				<Thumb src={shown} {name} class="size-full rounded-full shadow-2xl" />
			{/if}
			{#if verified}
				<span
					title="Verified"
					class="absolute right-[7%] bottom-[7%] flex size-9 items-center justify-center rounded-full bg-card"
				>
					<BadgeCheck class="size-6" aria-label="Verified" />
				</span>
			{/if}
		</div>
	</div>
</CoverPanel>

{#if draft}
	<CoverEditor bind:open={changing} known={[]} onpick={(cover) => (draft.cover = cover)} />
{/if}

{#if viewing && shown}
	<CoverViewer
		covers={[{ url: shown, thumb: shown }]}
		bind:index
		onclose={() => (viewing = false)}
	/>
{/if}
