// frontend/src/main.js
// Main entry point for Vue app

import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

// Initialize Vue app
createApp(App).use(router).mount("#app");

// Log Supabase connection status (for debugging)
import { supabase } from "./lib/supabase";
console.log(
    "Supabase client initialized:",
    supabase ? "Connected" : "Failed",
);
