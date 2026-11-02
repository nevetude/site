<script lang="ts">
	import Disclosure from '#lib/components/disclosure.svelte';

	type Props = {
		fetchRaw: () => Promise<object | null | undefined>; // null: a stub has no response
		stub: string;
	};

	let { fetchRaw, stub }: Props = $props();

	let text = $state<string | null>(null);
	let loading = $state(false);

	// Loaded when it is opened: the answer is a few tens of KB nobody needs until they ask.
	async function load() {
		if (text !== null) return;
		loading = true;
		try {
			const data = await fetchRaw();
			text = data ? JSON.stringify(data, null, 2) : stub;
		} catch {
			text = 'The response did not load.';
		} finally {
			loading = false;
		}
	}
</script>

<Disclosure title="Genius response (raw)" onopen={load}>
	<pre class="max-h-[28rem] overflow-auto font-mono text-xs text-muted-foreground">{loading
			? 'Loading…'
			: text}</pre>
</Disclosure>
