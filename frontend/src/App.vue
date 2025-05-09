<!-- src/App.vue -->
<template>
  <div id="app">
    <router-view></router-view>
  </div>
</template>

<script>
export default {
  name: 'App',

  mounted: function () {
    // Initialize any app-wide services or state
    this.initializeApp();
  },

  methods: {
    initializeApp: function () {
      // Check for authentication on page load
      const token = localStorage.getItem('token');

      if (token) {
        // Validate token or refresh if needed
        console.log('Token found, app initialized');
      }
    }
  }
}
</script>

<style>
/* Global styles applied to the entire app */
html,
body {
  height: 100%;
  margin: 0;
  padding: 0;
}

#app {
  height: 100%;
  font-family: 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>