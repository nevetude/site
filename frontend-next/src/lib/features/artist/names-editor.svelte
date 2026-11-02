<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import { Button } from '#lib/components/ui/button/index.js';
	import type { ArtistDraft, DraftNickname } from '#lib/features/artist/artist-draft.svelte.js';
	import NicknameCard from '#lib/features/artist/nickname-card.svelte';

	// The names of the artist: the main ones (one after another in time, a name can come back) and the alter egos (names
	// on some releases). The aliases that Genius gave are not sorted into either yet: they are dragged into one of the
	// two lists, or taken away with the cross.
	type Props = { draft: ArtistDraft | null; artistId: number };

	let { draft = $bindable(), artistId }: Props = $props();

	let nextKey = $state(10_000);
	let over = $state<DraftNickname['kind'] | null>(null); // the list an alias is being dragged over

	function add(kind: DraftNickname['kind'], text = '') {
		if (!draft) return;
		const made: DraftNickname = {
			key: nextKey++,
			kind,
			name: text,
			spellings: [],
			periods: kind === 'main' ? [{ start: null }] : [],
			uses: []
		};
		if (kind === 'main') draft.mains = [...draft.mains, made];
		else draft.egos = [...draft.egos, made];
	}

	const taken = $derived(
		new Set([...(draft?.mains ?? []), ...(draft?.egos ?? [])].map((n) => n.name))
	);
	const unsorted = $derived((draft?.aliases ?? []).filter((alias) => !taken.has(alias)));

	const drop = (kind: DraftNickname['kind']) => (event: DragEvent) => {
		event.preventDefault();
		over = null;
		const alias = event.dataTransfer?.getData('text/plain');
		if (alias) add(kind, alias);
	};
	const hover = (kind: DraftNickname['kind']) => (event: DragEvent) => {
		event.preventDefault(); // allows the drop
		over = kind;
	};
	const GROUP = 'space-y-2 rounded-lg transition-colors duration-200';
</script>

{#if draft}
	<section
		class="space-y-4 pb-4 [&_.text-sm]:text-[12px] [&_.text-xs]:text-[12px]"
		aria-label="Names"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="{GROUP} {over === 'main' ? 'bg-foreground/10' : ''}"
			ondragover={hover('main')}
			ondragleave={() => (over = null)}
			ondrop={drop('main')}
		>
			<h3 class="text-[12px] text-subtle">Main names</h3>
			{#each draft.mains as nickname, i (nickname.key)}
				<NicknameCard
					bind:nickname={draft.mains[i]}
					{artistId}
					onremove={() => (draft.mains = draft.mains.filter((n) => n !== nickname))}
				/>
			{/each}
			<Button onclick={() => add('main')}><Plus /> main name</Button>
		</div>

		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="{GROUP} {over === 'alter_ego' ? 'bg-foreground/10' : ''}"
			ondragover={hover('alter_ego')}
			ondragleave={() => (over = null)}
			ondrop={drop('alter_ego')}
		>
			<h3 class="text-[12px] text-subtle">Alter egos</h3>
			{#each draft.egos as nickname, i (nickname.key)}
				<NicknameCard
					bind:nickname={draft.egos[i]}
					{artistId}
					onremove={() => (draft.egos = draft.egos.filter((n) => n !== nickname))}
				/>
			{/each}
			<Button onclick={() => add('alter_ego')}>
				<Plus /> alter ego
			</Button>
		</div>

		{#if unsorted.length}
			<div class="space-y-2">
				<h3 class="text-[12px] text-subtle">From Genius</h3>
				<ul class="flex flex-wrap gap-1.5" aria-label="Aliases of Genius">
					{#each unsorted as alias (alias)}
						<li
							draggable="true"
							ondragstart={(event) => event.dataTransfer?.setData('text/plain', alias)}
							ondragend={() => (over = null)}
							class="inline-flex cursor-grab items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[12px] hover:bg-muted/70 active:cursor-grabbing"
						>
							{alias}
							<button
								type="button"
								class="text-subtle hover:text-destructive"
								aria-label="Take away {alias}"
								onclick={() => (draft.aliases = draft.aliases.filter((a) => a !== alias))}
							>
								<X class="size-3" />
							</button>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</section>
{/if}
