<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import X from '@lucide/svelte/icons/x';
	import { cn } from '#lib/utils/cn.js';
	import { getDialog } from './dialog.svelte';

	let { class: className, children }: { class?: string; children: Snippet } = $props();

	const dialog = getDialog();

	const modal = (node: HTMLDialogElement) => node.showModal();
</script>

<!-- The `<dialog>` is the whole screen and has no ground of its own, so a press on it is a press outside the window. -->
{#if dialog.open}
	<dialog
		use:modal
		data-slot="dialog"
		class="fixed inset-0 m-0 h-dvh max-h-none w-dvw max-w-none items-center justify-center bg-transparent p-0 text-popover-foreground backdrop:bg-black/10 backdrop:backdrop-blur-xs open:flex"
		onclose={() => dialog.close()}
		onclick={(event) => event.target === event.currentTarget && dialog.close()}
	>
		<div
			data-slot="dialog-content"
			class={cn(
				'animate-pop relative grid w-full max-w-[calc(100vw-1.75rem)] gap-6 rounded-xl bg-popover p-6 text-sm shadow-2xl sm:max-w-md',
				className
			)}
		>
			{@render children()}
			<Button
				variant="close"
				size="icon"
				class="absolute top-3 right-3"
				aria-label="Close"
				onclick={() => dialog.close()}
			>
				<X />
			</Button>
		</div>
	</dialog>
{/if}
