<template>
  <div style="max-width: 1280px; margin: auto; padding: 0 1rem;">

    <p style="font-size: 1.6em; font-weight: bold;">
      Discord Dictionary Bot
    </p>
    <p style="font-size: 1.1em;">
      A Discord bot that can fetch definitions and post them in chat. If you are connected to a voice channel, the bot
      can also read out the definition to you. Dictionary bot can also translate words and phrases to many different
      languages!
    </p>

    <button class="mdc-button mdc-button--raised" data-mdc-auto-init="MDCButton"
            onclick="location.href='https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands'"
            type="button">
      <span class="mdc-button__label">Invite</span>
    </button>

    <p style="font-size: 1.3em; font-weight: bold;">
      Definitions
    </p>

    <div ref="image_container_define" class="image-container">
      <img src="define_sunflower.jpg" class="demo-image">
      <img src="define_gracias.jpg" class="demo-image">
    </div>

    <p style="font-size: 1.3em; font-weight: bold;">
      Translations
    </p>

    <div ref="image_container_translate" class="image-container">
      <img src="translate_english_spanish.jpg" class="demo-image">
      <img src="translate_dutch_english.jpg" class="demo-image">
    </div>

  </div>
</template>

<script setup>

import {onMounted, ref} from "vue";

const image_container_define = ref(null);
const image_container_translate = ref(null);

function getHorizontalScrollPercent(element) {
  return (element['scrollLeft'] || document.body['scrollLeft']) / ((element['scrollWidth'] || document.body['scrollWidth']) - element.clientWidth) * 100;
}

function addHorizontalScroller(element) {
  element.addEventListener("wheel", (event) => {
    const HORIZONTAL_SCROLL_AMOUNT = 40;
    if (getHorizontalScrollPercent(element) < 100 && event.deltaY > 0) {
      event.preventDefault();
      element.scrollBy({
        left: HORIZONTAL_SCROLL_AMOUNT
      })
    }
    if (getHorizontalScrollPercent(element) > 0 && event.deltaY < 0) {
      event.preventDefault();
      element.scrollBy({
        left: -HORIZONTAL_SCROLL_AMOUNT
      })
    }
  });
}

onMounted(() => {
  addHorizontalScroller(image_container_define.value);
  addHorizontalScroller(image_container_translate.value);
})

</script>

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
  overflow: auto;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

/* Track */
::-webkit-scrollbar-track {
  background: #f1f1f130;
  border-radius: 40px;
}

/* Handle */
::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 40px;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: #6e6e6e;
}

</style>
