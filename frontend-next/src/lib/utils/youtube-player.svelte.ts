import { YOUTUBE_ORIGIN, youtubeEmbedUrl } from '#lib/utils/dom.js';

/** A clip as the player needs it: the id on YouTube and the second it starts at. */
export type Clip = { id: string; start: number };

/**
 * The one YouTube player of a page and what the page knows about it. The first clip is opened by the address of the
 * player; the next ones are loaded into the same player by a command (it is not made again, so it stays on the whole
 * screen and there is no new entry in the history of the page). The page gives the `<iframe>` to `frame`
 * (`bind:this`), shows it while `embed` is not null, calls `listen` when it has loaded and passes the messages of the
 * window to `onmessage`.
 */
export class YoutubePlayer {
	frame = $state<HTMLIFrameElement | null>(null);
	/** The address the player was opened with; null: there is no player. */
	embed = $state<string | null>(null);
	/** The clip in the player is not paused and not over (it starts by itself). */
	sounding = $state(true);
	/** The picture of the player is hidden (a black screen) while a clip is changed, and shown again, smoothly, when the
	 * new clip has begun; a clip that does not begin in time is shown anyway. */
	hidden = $state(false);

	private ready = false; // the player has answered, so it takes commands
	private showTimer: ReturnType<typeof setTimeout> | undefined;

	constructor(private onended?: () => void) {}

	/** Fades the picture out before another clip is loaded. */
	hide() {
		this.hidden = true;
		clearTimeout(this.showTimer);
		this.showTimer = setTimeout(() => (this.hidden = false), 3000);
	}

	open(clip: Clip) {
		if (this.embed !== null && this.ready) {
			this.tell({
				event: 'command',
				func: 'loadVideoById',
				args: [{ videoId: clip.id, startSeconds: clip.start }]
			});
		} else {
			this.ready = false;
			// `enablejsapi`: the player tells the page when a clip is over.
			this.embed = youtubeEmbedUrl(clip.id, clip.start, {
				autoplay: '1',
				enablejsapi: '1',
				origin: location.origin
			});
		}
		this.sounding = true;
		// The button that started the clip keeps the keyboard otherwise, and the arrows would not wind the clip. A first clip
		// has no frame yet: it is focused when the frame has loaded (`listen`).
		this.frame?.focus();
	}

	close() {
		this.embed = null;
		this.ready = false;
		this.hidden = false;
		clearTimeout(this.showTimer);
	}

	/** The button of the clip that is in the player pauses and resumes it; the state comes back from the player, so the
	 * button also follows the controls of the player itself. */
	toggle = () =>
		this.tell({ event: 'command', func: this.sounding ? 'pauseVideo' : 'playVideo', args: [] });

	private tell(message: object) {
		this.frame?.contentWindow?.postMessage(JSON.stringify(message), YOUTUBE_ORIGIN);
	}

	/** The player reports its state once it has been told that somebody listens. The keyboard goes to it, to wind the clip. */
	listen = () => {
		this.tell({ event: 'listening', channel: 'widget' });
		this.frame?.focus();
	};

	onmessage = (event: MessageEvent) => {
		if (event.origin !== YOUTUBE_ORIGIN || event.source !== this.frame?.contentWindow) return;
		this.ready = true;
		const data = JSON.parse(event.data);
		const state = data.event === 'onStateChange' ? data.info : data.info?.playerState;
		if (typeof state === 'number') this.sounding = state !== 0 && state !== 2; // 0: over, 2: paused
		if (state === 1) {
			clearTimeout(this.showTimer);
			this.hidden = false; // the new clip has begun: it fades in
		}
		if (state === 0) this.onended?.();
	};
}
