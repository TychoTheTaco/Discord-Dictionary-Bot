<template>
   <div style="max-width: 1280px; margin: auto;">

    <p style="font-size: 1.6em; font-weight: bold;">
      Discord Dictionary Bot
    </p>
    <p style="font-size: 1.2em;">
      A Discord bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot can also read out the definition to you. Dictionary bot can also translate words and phrases to many different languages!
    </p>

    <button class="mdc-button mdc-button--raised" data-mdc-auto-init="MDCButton" onclick="location.href='https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands'" type="button">
      <span class="mdc-button__label">Invite</span>
    </button>

  </div>
</template>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>

@import "https://unpkg.com/material-components-web@latest/dist/material-components-web.min.css";

* {
  --mdc-theme-primary: #ff6d00;
  --mdc-theme-secondary: #ff6d00;
  --mdc-theme-on-primary: whitesmoke;
  --mdc-theme-on-surface: red;
}

</style>
