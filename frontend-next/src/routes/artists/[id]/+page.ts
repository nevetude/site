import { api } from '#lib/api/client.js';
import { loaded } from '#lib/utils/load.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => ({
	artist: await loaded(
		'artist',
		api.GET('/api/v1/artists/{artist_id}', {
			params: { path: { artist_id: Number(params.id) } },
			fetch
		})
	)
});
