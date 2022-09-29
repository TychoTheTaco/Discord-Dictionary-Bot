<template>
	<Header/>
	<div style="flex: 1;">
		<router-view/>
	</div>
	<Footer style="margin-top: 3rem;"/>
</template>

<style>

:root {
    --red: #BA2944;
    --blue: #1565C0;
    --yellow: #F9A825;
    --green: #2E7D32;
    --orange: #EF6C00;
    --purple: #6A1B9A;
    --pink: #AD1457;
    --light-green: #558B2F;
}

* {
    color: whitesmoke;
    font-family: "Segoe UI", sans-serif;
}

body {
    background-color: #141518;
    margin: 0;
}

code {
    font-family: Consolas, "courier new", monospace;
    background-color: #303030;
    padding: 2px 4px;
	border-radius: 3px;
}

</style>

<script>

import Header from "@/components/Header";
import Footer from "@/components/Footer";

export default {
	components: {Footer, Header}
}

</script>