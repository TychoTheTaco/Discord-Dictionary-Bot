<template>

	<div style="background-color: #303030; border-radius: 16px; margin: 16px; padding: 8px; position: relative;" ref="container">
		<canvas width="500" height="300" style="display: block; text-align: center;" ref="canvas"></canvas>
		<div ref="loading" style="height: 100%; width: 100%; position: absolute; top: 0; display: flex; align-items: center; justify-content: center">Loading...</div>
	</div>

</template>

<script>

export default {
	name: 'Graph',
	methods: {
		load(f) {
			(async () => {
				this.$refs.loading.style.visibility = 'visible';
				await f(this.$refs.container, this.$refs.canvas);
				this.$refs.loading.style.visibility = 'hidden';
			})().catch((error) => {
				console.log(error);
			});
		}
	}
}

</script>
