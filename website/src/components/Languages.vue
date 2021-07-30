<template>
	<h1>
		Languages
	</h1>
	<p>
		Some description
	</p>

	<h1>
		Languages
	</h1>


</template>

<script>
import json from '../commands.json'
export default {
	name: "Settings",
	data: () => {
		return {
			settings: json
		}
	}
}
</script>

<style scoped>

hr {
    margin: 2rem 0 2rem;
}

</style>
