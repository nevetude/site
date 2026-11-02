<script lang="ts">
	import { Input } from '#lib/components/ui/input/index.js';
	import ResetField from '#lib/features/edit/reset-field.svelte';

	// The title and the subtitle of an album or a song in the edit mode, in the place of the title of the page.
	type Draft = {
		baseName: string;
		variant: string;
		reset: { title: boolean; variant: boolean };
		edited(field: string): boolean;
	};
	type Props = { draft?: Draft | null; placeholder: string };

	let { draft = $bindable(null), placeholder }: Props = $props();
</script>

{#if draft}
	<ResetField edited={draft.edited('base_name')} bind:reset={draft.reset.title} label="title">
		<Input
			bind:value={draft.baseName}
			aria-label="Title"
			disabled={draft.reset.title}
			class="h-auto border-transparent py-1 text-[1.2rem] font-bold md:text-[1.2rem]"
		/>
	</ResetField>
	<ResetField edited={draft.edited('variant')} bind:reset={draft.reset.variant} label="subtitle">
		<Input
			bind:value={draft.variant}
			aria-label="Subtitle"
			{placeholder}
			disabled={draft.reset.variant}
			class="border-transparent"
		/>
	</ResetField>
{/if}
