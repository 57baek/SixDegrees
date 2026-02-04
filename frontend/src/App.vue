<!--
ROOT COMPONENT - This is the main wrapper for our whole app
-->

<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
// No imports needed - router-view handles everything
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
</style>
