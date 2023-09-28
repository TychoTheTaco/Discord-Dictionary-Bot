<template>
	<h1>
		Settings
	</h1>
	<p>
		Settings can be changed for the whole server (guild) or for individual channels. Channel settings take priority over server settings.
	</p>

	<h1>
		Settings
	</h1>

	<div v-for="(setting, index) in settings" v-bind:key="setting">
		<code>{{ setting.name }}</code> - {{ setting.description }}
		<div style="margin-left: 2rem;">
			<p>
				<b>Default: </b><code>{{ setting.default }}</code>
			</p>
			<div v-if="setting.choices !== undefined">
				<div>
					<b>Choices:</b>
					<div style="margin-left: 2rem;">
						<p v-for="choice in setting.choices" :key="choice">
							<code>{{ choice.name }}</code> - <span v-html="parseMarkdown(choice.description)"></span>
						</p>
					</div>
				</div>
			</div>
			<div v-else-if="setting.type === 'boolean'">
				<div>
					<b>Choices:</b>
					<div style="margin-left: 2rem;">
						<p><code>true</code></p>
						<p><code>false</code></p>
					</div>
				</div>
			</div>
		</div>
		<hr v-if="index !== settings.length - 1">
	</div>

</template>

<script>
import json from '@/assets/settings.json'
import {marked} from 'marked'

export default {
	name: "Settings",
	data: () => {
		return {
			settings: json
		}
	},
	methods: {
		parseMarkdown(text){
			return marked.parseInline(text);
		}
	}
}
</script>

<style scoped>

hr {
    margin: 2rem 0 2rem;
}

</style>
