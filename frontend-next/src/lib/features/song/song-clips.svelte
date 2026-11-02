<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import type { Snippet } from 'svelte';
	import type { AlbumVideo, SongDetail } from '#lib/api/client.js';
	import ExtLink from '#lib/components/ext-link.svelte';
	import PlayerFrame from '#lib/components/player-frame.svelte';
	import VideoTile from '#lib/components/video-tile.svelte';
	import { formatCount } from '#lib/utils/format.js';
	import { youtubeClip } from '#lib/utils/dom.js';
	import { YoutubePlayer } from '#lib/utils/youtube-player.svelte.js';

	// The cover, and the clip of the song lying over its lower edge, the way the tracklist of an album does (the page
	// pulls the cover's lower edge under the clip with `-mb-12` from 1000px wide; narrower there is a gap). A song has
	// one clip: a picture with a button and a sign: the title and the artists, then who made the clip. Pressed, the
	// picture becomes the player in the same place (the sign stays under it), and nothing else on the page changes.
	type Props = {
		song: SongDetail; // the sign says its title and artists; only their names get the tint
		videos: AlbumVideo[];
		tint?: string; // the ground of the sign: the colour of the cover, darker than the big card
		cover: Snippet<[boolean]>; // told whether a clip lies over its lower edge
	};

	let { song, videos, tint, cover }: Props = $props();

	// Only YouTube is embedded; a clip on another site has nothing to show here.
	const clip = $derived(
		videos.flatMap((video) => {
			const found = youtubeClip(video.url, video.start_seconds);
			return found ? [{ ...video, ...found }] : [];
		})[0]
	);

	// Every field the clip has: where it is, from which second it plays, and the two marks set by hand.
	const fields = $derived(
		clip
			? [
					{ label: 'Year', value: song.release_date?.slice(0, 4) ?? '-' },
					{ label: 'Source', value: 'YouTube' },
					{
						label: 'Starts at',
						value: `${Math.floor(clip.start / 60)}:${String(clip.start % 60).padStart(2, '0')}`
					},
					{ label: 'Official', value: clip.official ? 'Yes' : 'No' },
					{ label: 'Explicit', value: clip.explicit ? 'Yes' : 'No' }
				]
			: []
	);
	let infoOpen = $state(false);
	const signText = $derived(
		`${song.artists.map((artist) => artist.base_name).join(', ')} - ${song.base_name}${song.variant ? ` ${song.variant}` : ''}`
	);

	const player = new YoutubePlayer();
	let playing = $state(false);

	function play() {
		if (!clip || playing) return;
		player.hide(); // the picture comes in smoothly when the clip has begun
		player.open(clip);
		playing = true;
	}
</script>

<svelte:window onmessage={player.onmessage} />

{#snippet frame()}
	<PlayerFrame {player} title={clip?.song_name} scale={0.75} />
{/snippet}

<!-- With a clip the gap to the block below is 14px (the page puts 21px between its blocks; a utility wins over that rule). -->
<div class={clip ? 'mb-4' : ''}>
	{@render cover(!!clip)}
	{#if clip}
		<!-- As round as the top of the tracklist of an album; a soft shadow lifts it off the panel. -->
		<div class="relative z-10 overflow-hidden rounded-xl shadow-[0_6px_18px_rgba(0,0,0,0.35)]">
			<VideoTile
				picture={clip.picture}
				label="Play {clip.song_name}"
				{tint}
				caption="pt-[13px] pb-[9px]"
				large
				player={playing ? frame : undefined}
				onplay={play}
			>
				<!-- The line of the clip is its sign: the artists and the title, and the chevron after them opens the details. -->
				<button
					type="button"
					aria-expanded={infoOpen}
					title={signText}
					class="group flex w-full items-center gap-1.5 text-left text-xs hover:text-white"
					onclick={() => (infoOpen = !infoOpen)}
				>
					<span class="min-w-0 truncate">{signText}</span>
					<ChevronRight
						class="size-3.5 shrink-0 text-muted-foreground transition-transform duration-200 group-hover:text-white {infoOpen
							? 'rotate-90'
							: ''}"
					/>
					{#if song.view_count}
						<span
							class="ml-auto shrink-0 tabular-nums text-muted-foreground"
							title="Views of the song">{formatCount(song.view_count)}</span
						>
					{/if}
				</button>
				<!-- The rows are always in the page, in a box that opens by its height, so the opening is smooth. -->
				<div
					class="grid transition-[grid-template-rows] duration-200 ease-out {infoOpen
						? 'grid-rows-[1fr]'
						: 'grid-rows-[0fr]'}"
				>
					<div class="min-h-0 overflow-hidden" inert={!infoOpen}>
						<dl class="mt-2 space-y-1 pt-2 text-[11px]">
							{#each fields as { label, value } (label)}
								<div class="grid grid-cols-[45%_minmax(0,1fr)] gap-2">
									<dt class="text-subtle">{label}</dt>
									<dd class="truncate text-body">{value}</dd>
								</div>
							{/each}
							<div class="grid grid-cols-[45%_minmax(0,1fr)] gap-2">
								<dt class="text-subtle">Link</dt>
								<dd class="truncate text-body">
									<ExtLink href={clip.url} class="hover:underline">{clip.url}</ExtLink>
								</dd>
							</div>
						</dl>
					</div>
				</div>
			</VideoTile>
		</div>
	{/if}
</div>
