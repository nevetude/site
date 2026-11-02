import { api } from '#lib/api/client.js';
import { loaded } from '#lib/utils/load.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const path = { album_id: Number(params.id) };
	const [album, tracks, videos, neighbors] = await Promise.all([
		loaded('album', api.GET('/api/v1/albums/{album_id}', { params: { path }, fetch })),
		loaded('album', api.GET('/api/v1/albums/{album_id}/tracks', { params: { path }, fetch })),
		loaded('album', api.GET('/api/v1/albums/{album_id}/videos', { params: { path }, fetch })),
		loaded('album', api.GET('/api/v1/albums/{album_id}/neighbors', { params: { path }, fetch }))
	]);
	return { album, tracks, videos, neighbors };
};
