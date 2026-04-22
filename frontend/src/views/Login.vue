<template>
    <div class="login-container">
        <div class="login-box">
          <h2>Log Into SixDegrees</h2>
            <form @submit.prevent="handleLogin">
                <div class="form-group">
                    <label>Email</label>
                    <input
                        v-model="email"
                        type="text"
                        placeholder="Enter email"
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
        <button class="signup-btn" @click="handleSignup">Sign up</button>
    </div>
</template>

<script setup>
import { ref } from "vue";
import { supabase } from "../lib/supabase";
import { useRouter } from "vue-router";

const router = useRouter();
const email = ref("");
const password = ref("");
const error = ref("");

/*
  Redirects to the signup page
*/
const handleSignup = async () => {
  router.push("/signup");
};

/*
  Logs the user in with email/pw, saves the session token,
  then redirects ti profile setup if not yet onboarded, otherwise to the home feed
*/
const handleLogin = async () => {
  error.value = "";

  try {
    const { data, error: loginError } =
      await supabase.auth.signInWithPassword({
        email: email.value,
        password: password.value,
      });

    if (loginError) {
      error.value = loginError.message;
      return;
    }

    // Save session token
    localStorage.setItem("supabase_token", data.session.access_token);

    // Get user data
    const user = data.user;

    // check if profile exists
    const { data: onboarded, error: profileError } = await supabase.rpc('is_onboarded');

    if (profileError) {
      error.value = "Cannot load profile.";
      return;
    }

    if (!onboarded) {
      router.push("/profile-setup");
    } else {
      // if user is admin, redirect to admin page
      const { data: adminStatus, error : adminError } = await supabase.rpc('is_admin')
      if (!adminError && adminStatus !== null && adminStatus) router.push('/admin')
      else router.push("/");
    }

  } catch (err) {
    error.value = "Login failed.";
  }
};
</script>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
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

h2{
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

.signup-btn {
  width: 100%;
  max-width: 400px;
  padding: 0.75rem;
  margin-top: 20px;
  background: #08478f;
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

.signup-btn:hover {
  background: #0c5dba;
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