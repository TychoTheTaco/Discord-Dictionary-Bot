<template>

	<p>
		<code>/{{ command.name }}</code> - {{ command.description }}
	</p>

	<div>

		<!-- Options -->
		<div v-if="command.args !== undefined">
			<b>Options: </b>
			<div v-for="arg in command.args" :key="arg" style="margin: 1rem 0 1rem 2rem;">
				<code :class="{ 'args-required' : arg.required}">{{arg.value}}</code> {{ arg.description }}
			</div>
		</div>

		<!-- Sub-command (Command Group) -->
		<div style="margin-left: 2rem;" v-if="command.sub_commands !== undefined">
			<div v-for="sub_command in command.sub_commands" :key="sub_command">
				<code>/{{ command.name }} {{ sub_command.name }}</code> - {{ sub_command.description }}
				<div style="margin-left: 2rem; margin-top: 1rem;">
					<b>Options: </b>
					<div v-for="arg in sub_command.args" :key="arg" style="margin: 1rem 0 1rem 2rem;">
						<code :class="{ 'args-required' : arg.required}">{{arg.value}}</code> {{ arg.description }}
					</div>
				</div>

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
