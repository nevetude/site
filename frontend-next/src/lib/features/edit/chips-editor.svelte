<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import { Input } from '#lib/components/ui/input/index.js';

	// A list of short names (the tags of a song) to take names out of and to add to; what is typed is added with Enter
	// (or when the field is left). `suggest` gives the names that are known for what is typed.
	type Props = {
		values: string[];
		label: string;
		placeholder?: string;
		suggest?: (text: string) => Promise<string[]>;
	};

	let { values = $bindable(), label, placeholder = 'add', suggest }: Props = $props();

	let text = $state('');
	let suggestions = $state<string[]>([]);
	let timer: ReturnType<typeof setTimeout>;
	const listId = $props.id();

	function add() {
		const name = text.trim();
		if (name && !values.includes(name)) values = [...values, name];
		text = '';
		suggestions = [];
	}

	function typed() {
		if (!suggest) return;
		clearTimeout(timer);
		const asked = text;
		timer = setTimeout(async () => {
			const found = asked.trim() ? await suggest(asked) : [];
			if (asked === text) suggestions = found;
		}, 250);
	}
</script>

<div class="flex flex-wrap items-center gap-1.5">
	{#each values as value (value)}
		<span class="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs">
			{value}
			<button
				type="button"
				class="text-subtle hover:text-destructive"
				aria-label="Take {value} out of {label}"
				onclick={() => (values = values.filter((v) => v !== value))}
			>
				<X class="size-3" />
			</button>
		</span>
	{/each}
	<Input
		bind:value={text}
		oninput={typed}
		aria-label={label}
		{placeholder}
		list={listId}
		onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), add())}
		onblur={add}
		class="h-7 w-36 border-transparent text-xs"
	/>
	<datalist id={listId}>
		{#each suggestions as name (name)}<option value={name}></option>{/each}
	</datalist>
</div>
