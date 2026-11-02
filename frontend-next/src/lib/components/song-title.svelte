<script lang="ts">
	import ExtLink from '#lib/components/ext-link.svelte';

	type Props = {
		song: { base_name: string; variant: string | null; genius_url: string | null };
		class?: string;
	};

	let { song, class: className = '' }: Props = $props();
</script>

<!-- The addition to the title (Live, Remix, ...) stays as text of the same size, darker; hovering shows the whole title. -->
<span
	class="min-w-0 truncate text-sm {className}"
	title={song.variant ? `${song.base_name} (${song.variant})` : song.base_name}
>
	{#if song.genius_url}
		<ExtLink href={song.genius_url} class="text-foreground hover:underline">
			{song.base_name}
		</ExtLink>
	{:else}
		<span class="text-foreground">{song.base_name}</span>
	{/if}
	{#if song.variant}<span class="text-subtle">{song.variant}</span>{/if}
</span>
