<script lang="ts">
	import CommaList from '#lib/components/comma-list.svelte';
	import { ofAlbum } from '#lib/utils/albums.js';

	// The artists of a song on one line, and after "feat." its guests. `main`: the artists of the page, whose names get
	// the tint (`CommaList`). The line is cut by its parent, not wrapped.
	type Name = { id: number; base_name: string };
	type Props = { artists: Name[]; featured: Name[]; main: { id: number }[] };

	let { artists, featured, main }: Props = $props();

	const names = (list: Name[]) => list.map((one) => one.base_name);
</script>

<CommaList
	items={names(artists)}
	wrap={false}
	tinted={ofAlbum(artists, main)}
/>{#if featured.length}<span class="mx-[0.3em]">feat.</span><CommaList
		items={names(featured)}
		wrap={false}
		tinted={ofAlbum(featured, main)}
	/>{/if}
