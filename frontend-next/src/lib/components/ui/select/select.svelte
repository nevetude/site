<script lang="ts" module>
	import { getContext, setContext } from 'svelte';

	export type SelectContext = {
		readonly value: string;
		open: boolean;
		readonly disabled: boolean;
		trigger: HTMLElement | null;
		pick: (value: string) => void;
	};

	export const setSelect = (ctx: SelectContext) => setContext('select', ctx);
	export const getSelect = () => getContext<SelectContext>('select');
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	// One value chosen from a list that opens under a button (a listbox). It is made of `Trigger` (the button, with the
	// chosen text as its children), `Content` (the list) and `Item` (a row); there is no element of its own.
	type Props = {
		value?: string;
		onValueChange?: (value: string) => void;
		disabled?: boolean;
		children: Snippet;
	};

	let { value = $bindable(''), onValueChange, disabled = false, children }: Props = $props();

	let open = $state(false);

	const ctx: SelectContext = {
		get value() {
			return value;
		},
		get open() {
			return open;
		},
		set open(next) {
			open = next;
		},
		get disabled() {
			return disabled;
		},
		trigger: null,
		pick(next) {
			value = next;
			onValueChange?.(next);
			open = false;
			ctx.trigger?.focus();
		}
	};
	setSelect(ctx);
</script>

{@render children()}
