/**
 * Calls `tick` over and over, `delay()` milliseconds after the previous call has finished (so slow answers never pile
 * up), until the returned function is called. The first call is made at once.
 */
export function poll(tick: () => Promise<void>, delay: () => number) {
	let timer: ReturnType<typeof setTimeout>;
	let stopped = false;

	const run = async () => {
		await tick();
		if (!stopped) timer = setTimeout(run, delay());
	};
	void run();

	return () => {
		stopped = true;
		clearTimeout(timer);
	};
}
