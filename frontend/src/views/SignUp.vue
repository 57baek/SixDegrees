<!-- 
SIGNUP PAGE - form users see when creating a new account 
-->
import { supabase } from "../lib/supabase";

<template>
    <div class="signup-container">
        <div class="signup-box">
          <h2>Create a SixDegrees Account</h2>
            <form @submit.prevent="handleSignUp">
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
                        @focus="showChecklist = true"
                        @blur="showChecklist = false"
                        @input="showChecklist = true"
                        placeholder="Enter Password"
                        required
                    />
                  <div v-if="showChecklist" class="pw-checklist" aria-live="polite">
                    <ul>
                      <li :class="{valid: validations.length, invalid: !validations.length}">
                        <span class="dot">{{ validations.length ? '✓' : '✕' }}</span>
                        At least 8 characters
                      </li>
                      <li :class="{valid: validations.upper, invalid: !validations.upper}">
                        <span class="dot">{{ validations.upper ? '✓' : '✕' }}</span>
                        At least 1 uppercase letter
                      </li>
                      <li :class="{valid: validations.lower, invalid: !validations.lower}">
                        <span class="dot">{{ validations.lower ? '✓' : '✕' }}</span>
                        At least 1 lowercase letter
                      </li>
                      <li :class="{valid: validations.number, invalid: !validations.number}">
                        <span class="dot">{{ validations.number ? '✓' : '✕' }}</span>
                        At least 1 number
                      </li>
                      <li :class="{valid: validations.special, invalid: !validations.special}">
                        <span class="dot">{{ validations.special ? '✓' : '✕' }}</span>
                        At least 1 special character (e.g. !@#$%)
                      </li>
                    </ul>
                  </div>
                </div>

                <div v-if="error" class="error">
                    {{ error }}
                </div>
                <button type="submit" class="signup-btn">
                    Sign Up
                </button>
            </form>
        </div>
        <button class="back2login-btn" @click="handleBack2Login">I have an account</button>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from "../lib/supabase";

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const showChecklist = ref(false)

const validations = computed(() => {
  const pw = password.value || ''
  return {
    length: pw.length >= 8,
    upper: /[A-Z]/.test(pw),
    lower: /[a-z]/.test(pw),
    number: /\d/.test(pw),
    special: /[^A-Za-z0-9]/.test(pw),
  }
})

async function handleSignUp() {
  if (!Object.values(validations.value).every(Boolean)) {
    error.value = 'Password does not meet the requirements.'
    return
  }

  error.value = ''

  const { data, error: signUpError } = await supabase.auth.signUp({
    email: email.value,
    password: password.value,
  })

  if (signUpError) {
    error.value = signUpError.message
    return
  }

  alert("Signup successful! You can now log in.")
  router.push("/login")
}

const handleBack2Login = async () => {
  router.push("/login");
};
</script>


<style scoped>
.signup-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  min-height: 100vh;
  background: #1a1a1a;
}

.signup-box {
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

p{
  color: #b0b0b0;
  margin: 5px 0px;
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

.signup-btn {
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

.back2login-btn {
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

.back2login-btn:hover {
  background: #0c5dba;
}

.signup-btn:hover {
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

.pw-checklist {
  margin-top: 0.5rem;
}
.pw-checklist ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.pw-checklist li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #cfcfcf;
  margin-bottom: 0.4rem;
}
.pw-checklist li .dot {
  display: inline-block;
  width: 1.2rem;
  text-align: center;
  font-weight: 700;
}
.pw-checklist li.valid {
  color: #8ef0a6;
}
.pw-checklist li.invalid {
  color: #fa7676;
  opacity: 0.75;
}
</style>