<template>
	<h1>
		Slash Commands
	</h1>
	<p>
		Options with a <code class="args-required">red</code> background are required; the rest are optional.
	</p>
	<hr>

	<div v-for="(command, index) in commands" v-bind:key="command.name">
		<Command v-bind:command="command"/>
		<hr v-if="index !== commands.length - 1">
	</div>
</template>

<script>
import Command from "@/components/Command";
import json from '@/assets/commands.json'
export default {
	name: "Commands",
	components: {Command},
	data: () => {
		return {
			commands: json
		}
	}
}
</script>

<style>

hr {
    margin: 2rem 0 2rem;
}

.args-required {
    font-family: Consolas, "courier new", monospace;
    background-color: #642424;
    padding: 2px 4px;
	border-radius: 3px;
}

</style>
