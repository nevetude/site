<script lang="ts">
	import type { DomNode, DomRef } from '#lib/utils/dom.js';
	import RichText from '#lib/components/rich-text.svelte';

	// `dom` is null for a description written by hand (it has no links or marks): then there is only the text.
	type Props = { dom: DomNode | null; text: string; refs: DomRef[] };

	let { dom, text, refs }: Props = $props();
</script>

<article class="rounded-xl bg-card p-5 text-sm leading-relaxed text-body">
	{#if dom}
		<RichText node={dom} {refs} />
	{:else}
		<p class="whitespace-pre-line">{text}</p>
	{/if}
</article>
