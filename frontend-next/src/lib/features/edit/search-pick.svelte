<script lang="ts" generics="T">
	import Plus from '@lucide/svelte/icons/plus';
	import { type Snippet, tick } from 'svelte';
	import { fade } from 'svelte/transition';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { openPopover } from '#lib/utils/popover.js';

	// A field that looks something up while it is typed in (`search` answers for the text) and lists what it found;
	// `onpick` is called for the one that is pressed, and the list closes (a pick, Escape, or a press anywhere else).
	// The list lies over the page and moves nothing. Used to pick an artist, a song or a release.
	// With `button` the field starts as a button with that text: pressed, it turns into the field (no hint inside) and
	// the list opens at once with what `search('')` answers, the newest ones; after a pick or a press away it is a
	// button again.
	type Props = {
		label: string; // for a screen reader: the field has a short grey hint
		placeholder?: string;
		button?: string;
		search: (text: string) => Promise<T[]>;
		onpick: (found: T) => void;
		row: Snippet<[T]>;
	};

	let { label, placeholder = 'name', button, search, onpick, row }: Props = $props();

	let text = $state('');
	let found = $state<T[] | null>(null);
	// The field itself is shown, not the button. `button` does not change while the component lives, so the start is enough.
	// svelte-ignore state_referenced_locally
	let active = $state(!button);
	let input = $state<HTMLInputElement | null>(null);
	let timer: ReturnType<typeof setTimeout>;
	let anchor = $state<HTMLElement>();
	let list = $state<HTMLElement>();
	const open = $derived(found !== null); // not `found` itself: a new answer must not open the list again

	function close() {
		found = null;
		if (button && !text.trim()) active = false;
	}

	$effect(() => {
		if (!open || !list || !anchor) return;
		return openPopover(list, anchor, close);
	});

	// A moment after the last key, so typing a name does not ask for every prefix of it.
	function typed() {
		clearTimeout(timer);
		if (!text.trim() && !button) {
			found = null;
			return;
		}
		const asked = text;
		timer = setTimeout(async () => {
			const answer = await search(asked);
			if (asked === text) found = answer;
		}, 250);
	}

	async function start() {
		active = true;
		found = await search('');
		await tick();
		input?.focus();
	}

	function pick(one: T) {
		onpick(one);
		text = '';
		close();
	}
</script>

<div bind:this={anchor} class="grid">
	{#if active}
		<div class="col-start-1 row-start-1" in:fade={{ duration: 150 }}>
			<Input
				bind:ref={input}
				bind:value={text}
				oninput={typed}
				aria-label={label}
				placeholder={button ? '' : placeholder}
			/>
		</div>
	{:else}
		<div class="col-start-1 row-start-1" out:fade={{ duration: 100 }}>
			<!-- Inter sits high in its line: measured, the capitals were 1px above the middle of the button, so the text is moved down by 1px.
			     The plus is 7px from the left, the top and the bottom edge (6px inside the 1px border, as the 28px height leaves above and below it). -->
			<Button
				class="w-full justify-start gap-1 pl-[6px] text-[12.5px] leading-none text-muted-foreground hover:text-foreground"
				onclick={start}
				><Plus strokeWidth={2.5} /><span class="translate-y-px">{button}</span></Button
			>
		</div>
	{/if}
</div>
<ul bind:this={list} popover="manual" aria-label="Found" class="popup min-w-64">
	{#each found ?? [] as one, i (i)}
		<li>
			<Button
				variant="ghost"
				class="h-auto w-full justify-start gap-3 px-3 py-1.5 font-normal"
				onclick={() => pick(one)}
			>
				{@render row(one)}
			</Button>
		</li>
	{:else}
		<li class="p-3 text-center text-sm text-muted-foreground">Nothing found</li>
	{/each}
</ul>
