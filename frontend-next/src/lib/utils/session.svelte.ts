import { api, type Me } from '#lib/api/client.js';

/** Who is looking at the site. The server decides on every write; this only says whether to show the pencil. */
class Session {
	me = $state<Me | null>(null);
	canEdit = $derived(this.me?.can_edit ?? false);

	async load() {
		try {
			this.me = (await api.GET('/api/v1/me')).data ?? null;
		} catch {
			this.me = null; // the backend is not running: the pages show their own error
		}
	}
}

export const session = new Session();
