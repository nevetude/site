<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ArtistDetail } from '#lib/api/client.js';
	import ImportInfo from '#lib/components/import-info.svelte';
	import RawResponse from '#lib/components/raw-response.svelte';

	// What is for the developer and not for the reader: one closed list at the very bottom of a detail page. What
	// `ImportInfo` needs is all on the entity itself; `children` adds more blocks of the page.
	type Props = {
		subject: 'artist' | 'album' | 'song';
		entity: Pick<ArtistDetail, 'created_at' | 'updated_at' | 'imports' | 'history'>;
		fetchRaw: () => Promise<object | null | undefined>;
		children?: Snippet;
	};

	let { subject, entity, fetchRaw, children }: Props = $props();
</script>

<div class="overflow-hidden rounded-xl bg-card">
	<ImportInfo
		{subject}
		createdAt={entity.created_at}
		updatedAt={entity.updated_at}
		imports={entity.imports}
		history={entity.history}
	/>
	<RawResponse stub="No raw response: the {subject} is a stub." {fetchRaw} />
	{@render children?.()}
</div>
