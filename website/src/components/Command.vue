<template>

	<h4>
		<code>{{ command.name }}</code>
	</h4>

	<p>
		{{ command.description }}
	</p>

	<p v-if="command.aliases !== undefined && command.aliases.length > 0">
		<b>Aliases: </b>
		<span v-for="(alias, index) in command.aliases" :key="alias">
			<code>{{ alias }}</code>
			<span v-if="index !== command.aliases.length - 1">, </span>
		</span>
	</p>

	<div v-if="command.args !== undefined">
		<b>Usage: </b>
		<code>
			{{ command.name }}

			<span v-for="(arg, index) in command.args" :key="arg">
				<span :class="{ 'args-required' : arg.required, 'args-optional' : !arg.required}"><!--
					-->{{ arg.value }}<!--
					--><span v-if="arg.args !== undefined">&nbsp;&nbsp;<!--
						--><span v-for="(arg1, index1) in arg.args" :key="arg1" class="code"><!--
							-->{{ arg1.value }}<!--
							--><span v-if="index1 !== arg.args.length - 1">&nbsp;&nbsp;</span>
						</span>
					</span>
				</span>

				<span v-if="index !== command.args.length - 1">&nbsp;&nbsp;</span>

			</span>

		</code>
		<div v-for="(arg) in command.args" :key="arg" style="margin: 1rem 0 1rem">
			<code v-html="formatArg(arg)"></code> {{ arg.description }}
			<div v-for="child_arg in arg.args" :key="child_arg" style="margin-left: 2rem;">
				<br>
				<code v-html="formatArg(child_arg)"></code> {{ child_arg.description }}
			</div>
		</div>
	</div>

</template>

<script>

export default {
	name: 'Command',
	props: {
		command: Object
	},
	methods: {
		formatArg(arg) {
			let container = arg.value;

			if (arg.args !== undefined && arg.args.length > 0) {
				container += " ";
				for (const child_arg of arg.args) {
					container += this.formatArg(child_arg);
				}
			}

			return container;
		}
	}
}

</script>

<style scoped>

.args-optional {
    font-family: Consolas, "courier new", monospace;
    background-color: #FFFF0020;
    border-radius: 0.2rem;
    padding: 0.1rem;
}

.args-required {
    font-family: Consolas, "courier new", monospace;
    background-color: #FF000040;
    border-radius: 0.2rem;
    padding: 0.1rem;
}

.code {
    font-family: Consolas, "courier new", monospace;
}

</style>
