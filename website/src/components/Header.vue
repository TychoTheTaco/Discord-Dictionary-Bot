<template>
	<nav style="background-color: #1B1C1F">

		<div style="max-width: 1280px; margin: auto;">

			<div ref="container" style="display: flex; flex-direction: row; justify-content: space-between; align-items: center;">

				<!-- Left -->
				<a href="/" style="display: flex; flex-direction: row; align-items: center; margin: 0.8rem; text-decoration: none;">
					<img src="/dictionary.png" alt="" width="48" height="48" style="border-radius: 50%;">
					<span style="font-size: 1.2em; font-weight: bold; margin-left: 1rem; white-space: nowrap;">Discord Dictionary Bot</span>
				</a>

				<!-- Right -->
				<div style="display: inline-block; font-size: 1.2em; margin-right: 1rem;" :class="{ 'hide' : menu_visible, '' : !menu_visible}">
					<a target="_blank" rel="noopener noreferrer" href="https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands" class="nav-link"><b>Invite</b></a>
					<a href="/" class="nav-link">Home</a>
					<a href="/docs/commands" class="nav-link">Documentation</a>
					<a target="_blank" rel="noopener noreferrer" href="https://github.com/TychoTheTaco/Discord-Dictionary-Bot" class="nav-link">GitHub</a>
					<a href="/statistics" class="nav-link">Statistics</a>
				</div>

				<img src="/menu.svg" alt="Menu" v-show="menu_visible" style="margin: 1rem 2rem;" v-on:click="toggleMenu"/>

			</div>

			<div style="display: flex; flex-direction: column;" v-show="menu_open">
				<a target="_blank" rel="noopener noreferrer" href="https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands" class="nav-link"><b>Invite</b></a>
				<a href="/" class="nav-link">Home</a>
				<a href="/docs/commands" class="nav-link">Documentation</a>
				<a target="_blank" rel="noopener noreferrer" href="https://github.com/TychoTheTaco/Discord-Dictionary-Bot" class="nav-link">GitHub</a>
				<a href="/statistics" class="nav-link">Statistics</a>
			</div>

		</div>

	</nav>
</template>

<script>
export default {
	name: 'Header',
	mounted() {
		window.addEventListener('resize', this.onWindowResize);
		this.onWindowResize();
	},
	unmounted() {
		window.removeEventListener('resize', this.onWindowResize);
	},
	data() {
		return {
			menu_visible: false,
			menu_open: false
		}
	},
	methods: {
		toggleMenu() {
			this.menu_open = !this.menu_open;
		},
		updateWidth() {
			let totalChildWidth = 0;
			for (const child of this.$refs.container.children) {
				totalChildWidth += child.clientWidth;
			}
			this.menu_visible = totalChildWidth >= this.$el.clientWidth
		},
		onWindowResize(){
			this.$nextTick(() => {
				this.updateWidth();
			});
		}
	}
}
</script>

<style scoped>

.nav-link {
    text-decoration: none;
    margin: 1rem;
}

.nav-link:hover {
    text-decoration: underline;
}

.hide {
    visibility: hidden;
    position: fixed;
}

</style>
