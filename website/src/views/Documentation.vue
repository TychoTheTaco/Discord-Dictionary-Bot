<template>
	<div style="max-width: 1280px; margin: auto; padding: 0 1rem;">
		<div style="display: flex; flex-direction: row; justify-content: center">
			<a href="/docs/commands" class="nav-link">Commands</a>
			<a href="/docs/settings" class="nav-link">Settings</a>
			<a href="/docs/languages" class="nav-link">Languages</a>
		</div>

		<div>
			<Commands v-if="$route.path === '/docs/commands'"/>
			<Settings v-if="$route.name === 'Settings'"/>
			<Languages v-if="$route.name === 'Languages'"/>
		</div>
	</div>

</template>

<script>
import Commands from "@/components/Commands";
import Settings from "@/components/Settings";
import Languages from "@/components/Languages";

export default {
	components: {Settings, Commands, Languages}
}
</script>

<style scoped>

.nav-link {
    text-decoration: none;
    margin: 1rem;
    font-size: 1.2em;
    font-weight: bold;
    background-color: #303030;
    border-radius: 0.4rem;
    padding: 0.4rem;
}

.nav-link:hover {
    text-decoration: underline;
}

</style>