import {createRouter, createWebHistory} from 'vue-router'
import Home from '../views/Home.vue'
import Statistics from "@/views/Statistics";
import Documentation from "@/views/Documentation";

const routes = [
	{
		path: '/',
		name: 'Home',
		component: Home
	},
	{
		path: '/statistics',
		name: 'Statistics',
		component: Statistics
	},
	{
		path: '/docs',
		name: 'Documentation',
		component: Documentation,
		redirect: '/docs/commands',
		children: [
			{
				path: 'commands',
				name: 'Commands',
				component: Documentation
			},
			{
				path: 'settings',
				name: 'Settings',
				component: Documentation
			},
			{
				path: 'languages',
				name: 'Languages',
				component: Documentation
			}
		]
	}
]

const router = createRouter({
	history: createWebHistory(process.env.BASE_URL),
	routes
})

export default router
