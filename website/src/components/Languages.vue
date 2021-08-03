<template>
	<h1>
		Languages
	</h1>
	<p>
		The following languages are supported for translations. Note that not all of them are supported by text-to-speech.
	</p>

	<div style="overflow-x: auto;">
		<table>
			<tr>
				<th>Language Name</th>
				<th>Language Code</th>
				<th>Text-to-Speech</th>
			</tr>
			<tr v-for="language in languages" :key="language">
				<td>{{ language.name }}</td>
				<td>{{ language.code }}</td>
				<td v-if="language.tts">Yes</td>
				<td v-else>No</td>
			</tr>
		</table>
	</div>

</template>

<script>
import languages from '@/assets/languages.json'

// Sort languages
languages.sort((a, b) => {
	return a['name'] < b['name'] ? -1 : 1;
});

export default {
	name: "Languages",
	data: () => {
		return {
			languages: languages
		}
	}
}
</script>

<style scoped>

th, td {
    padding: 0 2rem;
}

table, th, td {
    border: 1px solid #FFFFFF30;
}

</style>
