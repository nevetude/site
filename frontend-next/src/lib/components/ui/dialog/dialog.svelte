<script lang="ts" module>
	import { getContext, setContext } from 'svelte';

	type Context = { open: boolean; close: () => void };

	export const setDialog = (ctx: Context) => setContext('dialog', ctx);
	export const getDialog = () => getContext<Context>('dialog');
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';

	// A modal window on the native `<dialog>`: the browser keeps the focus inside, closes it with Escape and puts the
	// page behind it out of reach. `onOpenChange` is told when the window wants to close (Escape, the cross, a press on
	// the dark ground); whoever owns `open` decides.
	type Props = { open?: boolean; onOpenChange?: (open: boolean) => void; children: Snippet };

	let { open = $bindable(false), onOpenChange, children }: Props = $props();

	setDialog({
		get open() {
			return open;
		},
		close() {
			open = false;
			onOpenChange?.(false);
		}
	});
</script>

{@render children()}
