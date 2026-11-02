<script lang="ts">
	import { tick } from 'svelte';
	import type { AlbumTrack, AlbumVideo } from '#lib/api/client.js';
	import CreditedLine from '#lib/components/credited-line.svelte';
	import PlayerFrame from '#lib/components/player-frame.svelte';
	import VideoTile from '#lib/components/video-tile.svelte';
	import { trackNumbers } from '#lib/utils/albums.js';
	import { youtubeClip } from '#lib/utils/dom.js';
	import { formatFullDate } from '#lib/utils/format.js';
	import { glide } from '#lib/utils/glide.js';
	import { YoutubePlayer } from '#lib/utils/youtube-player.svelte.js';
	import VideoCredits from '#lib/features/album/video-credits.svelte';

	// `playing` is the clip in the main place (the page puts this block in another place when there is one and moves
	// its other blocks, `others`, with it); `push` is the room the page asks for above.
	type Props = {
		videos: AlbumVideo[];
		tracks: AlbumTrack[]; // what the clips are signed with: the number of the track and its artists
		main: { id: number }[]; // the artists of the album: only their names get the tint
		tint?: string; // the ground of the signs and of the credits: the colour of the cover, darker than the big card
		playing?: string | null;
		others?: () => (HTMLElement | null | undefined)[];
		top?: () => HTMLElement | null; // the block whose lower edge goes under the bar of the site when a clip starts
		push?: number;
		single?: boolean; // one clip to a row while none is in the main place, for a column that is wide enough for one
		class?: string;
	};

	let {
		videos,
		tracks,
		main,
		tint,
		playing = $bindable(null),
		others = () => [],
		top = () => null,
		push = 0,
		single = false,
		class: className = ''
	}: Props = $props();

	// The clips Genius links from the songs of the album, the way the description shows a clip. Only YouTube is
	// embedded; the other sites have nothing to show here. A clip is a picture with a button (the picture is cached
	// by the browser, and a page of many clips does not load a player for each of them). There is one player, in the
	// main place: a pressed clip is played there instead of the one that played before, so two clips never play at
	// once, and the one that played before is a picture in the row again. When a clip is over the next one of the
	// tracklist is played, like a playlist; after the last one the player stays.
	const numbers = $derived(trackNumbers(tracks));
	const players = $derived(
		videos.flatMap((video) => {
			const clip = youtubeClip(video.url, video.start_seconds);
			if (!clip) return [];
			// Every clip is of a song of the tracklist: the server joins them.
			const track = tracks.find((one) => one.song_id === video.song_id)!;
			return [
				{
					...video,
					...clip,
					number: numbers[track.id],
					year: video.release_date?.slice(0, 4),
					date: formatFullDate(video.release_date, video.release_date_precision),
					track
				}
			];
		})
	);
	const current = $derived(players.find((video) => video.url === playing));

	const player = new YoutubePlayer(() => {
		const next = players[players.findIndex((video) => video.url === playing) + 1];
		if (next) void play(next.url);
	});

	let figures = $state<Record<string, HTMLElement | null>>({});
	let box = $state<HTMLElement | null>(null); // the main player
	const FADE_MS = 250;

	// Every clip and every block of the page glides from the place it was in to the place it is in now.
	const moving = () => [...Object.values(figures), ...others()];

	async function play(url: string) {
		const video = players.find((one) => one.url === url);
		if (!video) return;
		// The clip that plays now fades out to black before the next one is loaded.
		player.hide();
		if (playing !== null) await new Promise((done) => setTimeout(done, FADE_MS));
		await glide(moving(), async () => {
			player.open(video);
			playing = url;
			await tick();
			// The page follows the player: when the block above it (`top`) has gone up past the bar of the site, the page
			// goes back up to where it ends, so the player and what stands beside it are in view; without that block, the
			// player is only kept on the screen.
			const edge = top()?.getBoundingClientRect().bottom;
			const bar = document.querySelector('header.sticky')?.getBoundingClientRect().bottom ?? 0;
			// Only up: when the header has gone past the bar. A page that is not scrolled that far stays where it is.
			if (edge !== undefined) {
				if (edge < bar) window.scrollBy({ top: edge - bar });
			} else box?.scrollIntoView({ block: 'nearest' });
		});
	}

	const close = () =>
		glide(moving(), async () => {
			playing = null;
			player.close();
			await tick();
		});
</script>

<svelte:window onmessage={player.onmessage} />

{#if players.length}
	<!-- Closed, the block stands in the second column under the description: two clips in a row. With a clip in the
	     main place the page makes the block as wide as both columns and puts it first: the player (all the room that
	     the credits leave) with the credits beside it, and the other clips four in a row under them. Under 1200px
	     it is one column, the player over the whole width. -->
	<section
		class="space-y-3 transition-[margin] duration-200 ease-out {className}"
		style:margin-top={push ? `${push}px` : undefined}
		aria-label="Videos"
	>
		{#if current}
			<!-- The player and the credits of the clip are one piece: no gap, the rounding only on the outer corners. -->
			<!-- The credits are as wide as one clip of the row below (four of them, `gap-3` apart): their left edge is the left
			     edge of the last clip. The player takes the rest, and the gap before the credits is part of it. -->
			<div class="grid min-[1200px]:grid-cols-[minmax(0,1fr)_calc((100%_-_1.97rem)_/_4)]">
				<div
					bind:this={box}
					class="relative aspect-video scroll-mt-16 overflow-hidden rounded-lg bg-black min-[1200px]:rounded-r-none"
				>
					<PlayerFrame {player} title={current.song_name} />
				</div>
				<VideoCredits
					info={{
						title: current.song_name,
						variant: current.track.variant,
						date: current.date,
						artists: current.track.artists,
						featured: current.track.featured,
						producers: current.track.producers
					}}
					{main}
					{tint}
					onclose={close}
					class="hidden min-[1200px]:block min-[1200px]:rounded-l-none"
				/>
			</div>
		{/if}
		<div
			class="grid gap-3 {single && !current ? 'grid-cols-1' : 'grid-cols-2'} {current
				? 'min-[1200px]:grid-cols-4'
				: ''}"
		>
			{#each players as video (video.url)}
				{@const here = video.url === playing}
				<!-- The clip that is in the player stays in its place in the row: its picture is dimmed, bars dance on it while
				     it sounds and the button pauses it; paused, the button is a play button again. The sign under the clip, in the
				     style of the card of the album: the title and, pressed to the right, the number of the track; under them,
				     smaller, the artists and, pressed to the right under the number, the year of the song. -->
				<VideoTile
					bind:ref={figures[video.url]}
					picture={video.picture}
					label={!here
						? `Play ${video.song_name}`
						: player.sounding
							? `Pause ${video.song_name}`
							: `Resume ${video.song_name}`}
					current={here}
					sounding={player.sounding}
					{tint}
					caption="py-[9px]"
					onplay={() => (here ? player.toggle() : play(video.url))}
				>
					<div class="flex items-baseline gap-2 text-xs">
						<span class="min-w-0 flex-1 truncate"
							>{video.song_name}{#if video.track.variant}<span class="ml-1.5 text-muted-foreground"
									>{video.track.variant}</span
								>{/if}</span
						>
						<span class="shrink-0 text-subtle tabular-nums">{video.number}</span>
					</div>
					<div
						class="mt-0.5 flex h-4 items-baseline gap-2 text-[11px] leading-4 text-muted-foreground"
					>
						<span class="min-w-0 flex-1 truncate">
							<CreditedLine artists={video.track.artists} featured={video.track.featured} {main} />
						</span>
						<span class="shrink-0 tabular-nums">{video.year}</span>
					</div>
				</VideoTile>
			{/each}
		</div>
	</section>
{/if}
