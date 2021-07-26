<template>
	<Header/>
	<router-view/>
</template>

<style>

* {
    color: whitesmoke;
    font-family: "Segoe UI", sans-serif;
    user-select: none;
}

body {
    background-color: #424242;
    margin: 0;
}

</style>

<script>

import Header from "@/components/Header";

export default {
	components: {Header}
}

</script>