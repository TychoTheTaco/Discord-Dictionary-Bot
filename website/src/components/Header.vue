<template>
  <nav style="background-color: #1B1C1F">

    <div style="display: flex; flex-direction: row; justify-content: space-between; align-items: center; max-width: 1280px; margin: auto;">

      <!-- Left -->
      <a href="/" style="display: flex; flex-direction: row; align-items: center; margin: 0.8rem; text-decoration: none;">
        <img src="dictionary.png" alt="" width="48px" height="48px" style="border-radius: 50%;">
        <span style="font-size: 1.2em; font-weight: bold; margin-left: 1rem;">Discord Dictionary Bot</span>
      </a>

      <!-- Right -->
      <div style="display: inline-block; font-size: 1.2em">
        <a href="https://discord.com/api/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands" class="nav-link">Invite</a>
        <a href="/documentation" class="nav-link">Commands</a>
        <a href="https://github.com/TychoTheTaco/Discord-Dictionary-Bot" class="nav-link">GitHub</a>
        <a href="/statistics" class="nav-link">Statistics</a>
      </div>

    </div>

  </nav>
</template>

<script>
export default {
  name: 'Header'
}
</script>

<style scoped>

.nav-link {
  text-decoration: none;
  margin: 1rem;
}

.nav-link:hover {
  text-decoration: underline;
}

</style>
