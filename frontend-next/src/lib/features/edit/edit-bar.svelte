<script lang="ts">
	import Pencil from '@lucide/svelte/icons/pencil';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { session } from '#lib/utils/session.svelte.js';

	// The pencil of a page, in the lower right corner of the window: it opens the edit mode, where it becomes Cancel and
	// Save. Only an editor sees it. Escape cancels.
	type Props = {
		editing: boolean;
		saving?: boolean;
		error?: string;
		onedit: () => void;
		onsave: () => void;
		oncancel: () => void;
	};

	let { editing, saving = false, error = '', onedit, onsave, oncancel }: Props = $props();
</script>

<svelte:window onkeydown={(event) => editing && event.key === 'Escape' && oncancel()} />

<!-- Fixed in the lower right corner of the window, so it is there wherever the page is scrolled, on the ground of the
     containers of the page. -->
{#if session.canEdit}
	<div
		class="fixed right-6 bottom-6 z-40 flex items-center gap-2 rounded-xl bg-card shadow-lg {editing
			? 'p-1.5 pl-3'
			: ''}"
	>
		{#if editing}
			{#if error}<span class="text-sm text-destructive">{error}</span>{/if}
			<Button variant="ghost" class="rounded-lg" onclick={oncancel} disabled={saving}>Cancel</Button
			>
			<Button class="rounded-lg" onclick={onsave} disabled={saving}>
				{#if saving}<Spinner />{/if}
				Save
			</Button>
		{:else}
			<Button
				variant="ghost"
				class="size-10 rounded-xl"
				aria-label="Edit the page"
				title="Edit the page"
				onclick={onedit}
			>
				<Pencil class="size-4" />
			</Button>
		{/if}
	</div>
{/if}
