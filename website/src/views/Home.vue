<template>
	<div style="max-width: 1280px; margin: auto; padding: 0 1rem;">

		<p style="font-size: 1.6em; font-weight: bold;">
			Discord Dictionary Bot
		</p>
		<p style="font-size: 1.1em;">
			A Discord bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot can also read out the definition to you. Dictionary bot can also translate words and phrases to many different languages!
		</p>

		<button class="mdc-button mdc-button--raised" data-mdc-auto-init="MDCButton" onclick="location.href='https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands'" type="button">
			<span class="mdc-button__label">Invite</span>
		</button>

		<p style="font-size: 1.3em; font-weight: bold;">
			Definitions
		</p>

		<div class="image-container">
			<img src="define_sunflower.jpg" class="demo-image">
			<img src="define_gracias.jpg" class="demo-image">
		</div>

		<p style="font-size: 1.3em; font-weight: bold;">
			Translations
		</p>

		<div class="image-container">
			<img src="translate_english_spanish.jpg" class="demo-image">
			<img src="translate_dutch_english.jpg" class="demo-image">
		</div>

	</div>
</template>

<style scoped>

* {
    --mdc-theme-primary: #ff6d00;
    --mdc-theme-secondary: #ff6d00;
    --mdc-theme-on-primary: whitesmoke;
    --mdc-theme-on-surface: red;
}

.demo-image {
	margin: 0.5rem;
	border-radius: 0.4rem;
	max-width: 600px;
}

.image-container {
	display: flex;
	flex-direction: row;
}

</style>
