// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import mermaid from 'astro-mermaid';

const repo = 'https://github.com/denvasylenko/dushes';

// https://astro.build/config
export default defineConfig({
	site: process.env.DOCS_SITE ?? 'https://denvasylenko.github.io',
	base: process.env.DOCS_BASE ?? '/dushes',
	vite: { server: { fs: { allow: ['..'] } } },
	integrations: [
		mermaid({ theme: 'neutral', autoTheme: true, mermaidConfig: { fontFamily: 'system-ui, sans-serif', flowchart: { curve: 'basis', htmlLabels: true } } }),
		starlight({
			title: 'formguide',
			description: 'A chat agent that guides people through large forms: shows where to click, answers from your documents, reads theirs and fills fields with their confirmation.',
			logo: { src: './src/assets/logo.svg', replacesTitle: false },
			favicon: '/favicon.svg',
			social: [{ icon: 'github', label: 'GitHub', href: repo }],
			editLink: { baseUrl: `${repo}/edit/main/site/` },
			lastUpdated: false,
			components: { PageTitle: './src/components/PageTitle.astro', SocialIcons: './src/components/SocialIcons.astro' },
			head: [{ tag: 'link', attrs: { rel: 'alternate', type: 'text/plain', title: 'llms.txt', href: `${process.env.DOCS_BASE ?? '/dushes'}/llms.txt` } }],
			customCss: ['@fontsource-variable/space-grotesk', '@fontsource/ibm-plex-mono/400.css', '@fontsource/ibm-plex-mono/500.css', './src/styles/theme.css'],
			expressiveCode: { themes: ['github-dark-default', 'github-light'], styleOverrides: { borderRadius: '10px' } },
			sidebar: [
				{ label: 'Get started', items: [
					{ label: 'Overview', slug: 'getting-started/overview' },
					{ label: 'Quickstart', slug: 'getting-started/quick-start' },
					{ label: 'Run the demo app', slug: 'getting-started/demo-app' },
				] },
				{ label: 'Backend', items: [
					{ label: 'Install and serve', slug: 'backend/install' },
					{ label: 'Configuration', slug: 'backend/configuration' },
					{ label: 'Models and providers', slug: 'backend/models' },
					{ label: 'Domain packs', slug: 'backend/domain-packs' },
					{ label: 'Business documents', slug: 'backend/knowledge' },
					{ label: 'Skills and tools', slug: 'backend/skills' },
					{ label: 'Persistence and history', slug: 'backend/persistence' },
					{ label: 'Prefill', slug: 'backend/prefill' },
					{ label: 'Deploy and secure', slug: 'backend/deploy' },
					{ label: 'Speed and tracing', slug: 'backend/observability' },
				] },
				{ label: 'Frontend', items: [
					{ label: 'Choose a client', slug: 'frontend/overview' },
					{ label: 'The chat widget', slug: 'frontend/chat-widget' },
					{ label: 'React', slug: 'frontend/react' },
					{ label: 'react-hook-form', slug: 'frontend/react-hook-form' },
					{ label: 'CopilotKit', slug: 'frontend/copilotkit' },
					{ label: 'Any AG-UI client', slug: 'frontend/agui-client' },
					{ label: 'Plain HTML', slug: 'frontend/plain-html' },
					{ label: 'Cards and answers', slug: 'frontend/cards' },
					{ label: 'Themes and styling', slug: 'frontend/themes' },
					{ label: 'Frontend tools', slug: 'frontend/frontend-tools' },
				] },
				{ label: 'Your form', items: [
					{ label: 'How the form and agent talk', slug: 'form/overview' },
					{ label: 'Register the skeleton', slug: 'form/skeleton' },
					{ label: 'Send the form each run', slug: 'form/state' },
					{ label: 'Value formats', slug: 'form/value-formats' },
					{ label: 'Build the components', slug: 'form/components' },
					{ label: 'Troubleshooting', slug: 'form/troubleshooting' },
				] },
				{ label: 'Concepts', collapsed: true, items: [
					{ label: 'System overview', slug: 'concepts/overview' },
					{ label: 'One turn', slug: 'concepts/turn' },
					{ label: 'What the model sees', slug: 'concepts/context' },
					{ label: 'Business documents', slug: 'concepts/knowledge' },
					{ label: 'User documents', slug: 'concepts/attachments' },
					{ label: 'Long conversations', slug: 'concepts/memory' },
					{ label: 'Architecture in text', slug: 'concepts/architecture' },
				] },
				{ label: 'Reference', collapsed: true, items: [
					{ label: 'Configuration keys', slug: 'reference/configuration' },
					{ label: 'HTTP API', slug: 'reference/http-api' },
					{ label: 'AG-UI events', slug: 'reference/agui-events' },
					{ label: 'Python API', slug: 'reference/python-api' },
					{ label: 'CLI', slug: 'reference/cli' },
					{ label: '<agui-chat> API', slug: 'reference/agui-chat' },
				] },
				{ label: 'Specifications', collapsed: true, items: [{ autogenerate: { directory: 'specifications' } }] },
			],
		}),
	],
});
