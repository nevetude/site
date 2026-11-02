<script lang="ts">
	import type { CreditGroup } from '#lib/api/client.js';
	import { sortRoles } from '#lib/utils/albums.js';
	import CreditNames from '#lib/features/album/credit-names.svelte';
	import FactRow from '#lib/components/fact-row.svelte';

	let { groups, main }: { groups: CreditGroup[]; main: { id: number }[] } = $props();
</script>

<dl>
	{#each sortRoles(groups) as group (group.role)}
		<FactRow label={group.role}><CreditNames artists={group.artists} {main} /></FactRow>
	{/each}
</dl>
