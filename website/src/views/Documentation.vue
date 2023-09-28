<template>
	<div style="max-width: 1280px; margin: auto; padding: 0 1rem;">
		<div style="display: flex; flex-direction: row; justify-content: center">
			<a href="/docs/commands" class="nav-link">Commands</a>
			<a href="/docs/settings" class="nav-link">Settings</a>
		</div>

		<div>
			<Commands v-if="$route.name === 'Commands'"/>
			<Settings v-if="$route.name === 'Settings'"/>
		</div>
	</div>

</template>

<script>
import Commands from "@/components/Commands";
import Settings from "@/components/Settings";

export default {
	components: {Settings, Commands}
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