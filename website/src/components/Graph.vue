<template>

	<div style="background-color: #303030; border-radius: 16px; margin: 16px; padding: 8px;" ref="container">
		<canvas width="500" height="300" style="display: block; margin-bottom: 24px;" ref="canvas"></canvas>
	</div>

</template>

<script>

export default {
	name: 'Graph',
	methods: {
		load(f) {
			(async () => {
				await f(this.$refs.container, this.$refs.canvas);
			})().catch((error) => {
				console.log(error);
			});
		}
	}
}

</script>
