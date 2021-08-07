<template>
	<div style="background-color: #1B1C1F">

		<div ref="container" style="display: flex; justify-content: space-between; align-items: end; max-width: 1280px; margin: auto; padding: 0.8rem;" class="desktop">

			<div style="display: inline-block; margin-right: 2rem;">
				<p>
					Created by Tycho Bellers
				</p>
				<p>
					<a href="mailto:tycho.developer@gmail.com">tycho.developer@gmail.com</a>
				</p>
			</div>

			<div style="display: inline-block;">
				<p>
					Discord Dictionary Bot is open source! Check it out on <a target="_blank" rel="noopener noreferrer" href="https://github.com/TychoTheTaco/Discord-Dictionary-Bot" class="nav-link">GitHub</a>!
				</p>
				<p>
					Join the <a target="_blank" rel="noopener noreferrer" href="https://discord.gg/JevjQDFBhc" class="nav-link"> support server</a> if you have any questions, comments, or just want to play with the bot!
				</p>
			</div>

		</div>

	</div>
</template>

<script>
export default {
	name: 'Footer',
	mounted() {
		window.addEventListener('resize', this.onWindowResize);
		this.onWindowResize();
	},
	unmounted() {
		window.removeEventListener('resize', this.onWindowResize);
	},
	methods: {
		onWindowResize() {
			this.$nextTick(() => {
				if (window.innerWidth < 700 || screen.availWidth < 700){
					this.$refs.container.className = 'mobile';
				} else {
					this.$refs.container.className = 'desktop';
				}
			});
		}
	}
}
</script>

<style scoped>

.desktop {
    flex-direction: row;
}

.mobile {
	flex-direction: column;
}

</style>
