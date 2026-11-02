import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// The site is client-only (`ssr = false`): a build is static files, and every address is answered by the
			// one page that starts the app.
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	// The icons are Svelte components, one file for each: they are compiled with the app. Pre-bundled, every new
	// icon makes the dev server optimize again and reload the page, and the page then breaks with "Cannot read
	// properties of undefined (reading 'call')" until it is loaded again by hand.
	optimizeDeps: { exclude: ['@lucide/svelte'] },
	// One address for the site and the API: the dev server forwards /api to the backend. 8081, because the
	// old site (`frontend/`) still stands on 8080 for comparison.
	server: { port: 8081, strictPort: true, proxy: { '/api': 'http://localhost:8000' } },
	preview: { port: 8081, proxy: { '/api': 'http://localhost:8000' } },
	test: {
		expect: { requireAssertions: true },
		environment: 'node',
		include: ['src/**/*.test.ts']
	}
});
