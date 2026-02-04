<!-- 
LOGIN PAGE - form users see when logging in 
TODO: When they click submit, POST to http://localhost:8000/auth/login 
TODO: If successful, save the token to localStorage and redirect them 
--> 

<template>
    <div class="login-container">
        <div class="login-box">
            <form @submit.prevent="handleLogin">
                <div class="form-group">
                    <label>Username</label>
                    <input
                        v-model="username"
                        type="text"
                        placeholder="Enter username"
                        required
                    />
                </div>

                <div class="form-group">
                    <label>Password</label>
                    <input
                        v-model="password"
                        type="password"
                        placeholder="Enter Password"
                        required
                    />
                </div>

                <div v-if="error" class="error">
                    {{ error }}
                </div>

                <button type="submit" class="login-btn">
                    Login
                </button>
            </form>
        </div>
    </div>
</template>

<script setup>
import { ref } from "vue";
import { supabase } from "../lib/supabase";

// define reactive variables
const username = ref("");
const password = ref("");
const error = ref("");

const handleLogin = async () => {
    error.value = "";

    try {
        const { data, error: supabaseError } = await supabase.auth.signInWithPassword({
            email: username.value,
            password: password.value,
        });

        if (supabaseError) {
            error.value = supabaseError.message;
            return;
        }

        // Save session token
        localStorage.setItem("supabase_token", data.session.access_token);

        alert("Login successful!");

    } catch (err) {
        error.value = "Cannot connect to Supabase";
        console.error(err);
    }
};
</script>




<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #1a1a1a;
}

.login-box {
  background: #2d2d2d;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  width: 100%;
  max-width: 400px;
}

h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: #ffffff;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: #b0b0b0;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #444;
  border-radius: 4px;
  font-size: 1rem;
  background: #1a1a1a;
  color: #ffffff;
}

input:focus {
  outline: none;
  border-color: #088F8F;
}

.login-btn {
  width: 100%;
  padding: 0.75rem;
  background: #088F8F;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.3s ease;
}

.login-btn:hover {
  background: #0CC6C6;
}

.error {
  color: #ff6b6b;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: #3d1f1f;
  border-radius: 4px;
  text-align: center;
  border: 1px solid #ff6b6b;
}
</style>