<script lang="ts">
	import type { Snippet } from 'svelte';
	import { cn } from '#lib/utils/cn.js';
	import { openPopover } from '#lib/utils/popover.js';
	import { getSelect } from './select.svelte';

	let { class: className, children }: { class?: string; children: Snippet } = $props();

	const select = getSelect();
	let el = $state<HTMLElement>();

	const options = () => [
		...(el?.querySelectorAll<HTMLElement>('[role="option"]:not([aria-disabled="true"])') ?? [])
	];

	// The list is a popover, so a card around the button cannot cut it. Opened, the focus goes to the chosen row.
	$effect(() => {
		if (!select.open || !el || !select.trigger) return;
		const away = openPopover(el, select.trigger, () => (select.open = false));
		(options().find((o) => o.getAttribute('aria-selected') === 'true') ?? options()[0])?.focus();
		return away;
	});

	let typed = '';
	let timer: ReturnType<typeof setTimeout>;

	function onkeydown(event: KeyboardEvent) {
		const rows = options();
		const at = rows.indexOf(document.activeElement as HTMLElement);
		switch (event.key) {
			case 'ArrowDown':
				rows[Math.min(at + 1, rows.length - 1)]?.focus();
				break;
			case 'ArrowUp':
				rows[Math.max(at - 1, 0)]?.focus();
				break;
			case 'Home':
				rows[0]?.focus();
				break;
			case 'End':
				rows.at(-1)?.focus();
				break;
			case 'Tab':
				select.open = false;
				return;
			default: {
				if (event.key.length !== 1 || event.ctrlKey || event.metaKey) return;
				// A word typed quickly finds the row that begins with it.
				typed += event.key.toLowerCase();
				clearTimeout(timer);
				timer = setTimeout(() => (typed = ''), 600);
				rows.find((o) => o.textContent?.trim().toLowerCase().startsWith(typed))?.focus();
				return;
			}
		}
		event.preventDefault();
	}
</script>

<div
	bind:this={el}
	popover="manual"
	role="listbox"
	tabindex="-1"
	data-slot="select-content"
	class={cn('popup min-w-36', className)}
	{onkeydown}
>
	{@render children()}
</div>
