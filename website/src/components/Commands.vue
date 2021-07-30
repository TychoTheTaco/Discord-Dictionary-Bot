<template>
	<h1>
		Command Prefix
	</h1>
	<p>
		The default command prefix is <code>.</code><br><br>If you forget the command prefix, just @mention the bot and it will respond with the current prefix.
	</p>

	<h1>
		Commands
	</h1>
	<p>
		Items with a <code class="args-required">red</code> background are required and items with a <code class="args-optional">yellow</code> background are optional.
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

<style scoped>

hr {
    margin: 2rem 0 2rem;
}

</style>
