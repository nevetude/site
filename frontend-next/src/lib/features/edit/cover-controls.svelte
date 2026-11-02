<script lang="ts">
	import { Button } from '#lib/components/ui/button/index.js';
	import CoverEditor, { type CoverDraft } from '#lib/features/edit/cover-editor.svelte';
	import ResetButton from '#lib/features/edit/reset-button.svelte';

	// The buttons in the corner of a cover (or a portrait) in the edit mode: change it, or put it back to Genius. The
	// panel it stands in is `relative`. `known`: the pictures to choose from, besides the address of another one.
	type Props = {
		draft: CoverDraft;
		noun: 'cover' | 'photo';
		known?: { url: string; thumb: string }[];
	};

	let { draft = $bindable(), noun, known = [] }: Props = $props();

	let changing = $state(false);
</script>

<div class="absolute top-2 left-2 z-10 flex items-center gap-1">
	<Button disabled={draft.reset.cover} onclick={() => (changing = true)}>
		Change {noun}
	</Button>
	<ResetButton edited={draft.edited('cover_url')} bind:reset={draft.reset.cover} label={noun} />
</div>

<CoverEditor bind:open={changing} {known} onpick={(cover) => (draft.cover = cover)} />
