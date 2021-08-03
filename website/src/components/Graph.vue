<template>

	<div style="position: relative;">

		<div style="background-color: #303030; border-radius: 16px; margin: 1rem; padding: 8px; position: relative; box-sizing: border-box;" ref="container">
			<canvas style="text-align: center;" ref="canvas"></canvas>
		</div>

		<div ref="loading" style="height: 100%; width: 100%; position: absolute; top: 0; display: flex; align-items: center; justify-content: center">Loading...</div>

	</div>


</template>

<script>

export default {
	name: 'Graph',
	mounted() {
		window.addEventListener('resize', this.onWindowResize);
		this.onWindowResize();
	},
	unmounted() {
		window.removeEventListener('resize', this.onWindowResize);
	},
	methods: {
		load(f) {
			(async () => {
				this.$refs.loading.style.visibility = 'visible';
				await f(this.$refs.container, this.$refs.canvas);
				this.$refs.loading.style.visibility = 'hidden';
			})().catch((error) => {
				console.log(error);
			});
		},
		onWindowResize() {
			this.$nextTick(() => {
				const div = this.$el.querySelector('div div');
				if (window.innerWidth < 700 || screen.availWidth < 700){
					div.style.width = 'calc(100% - 2rem)';
					div.style.height = `${parseInt(getComputedStyle(div).width) * 0.55}px`;
				} else {
					div.style.width = '500px';
					div.style.height = '275px';
				}
			});
		}
	}
}

</script>
