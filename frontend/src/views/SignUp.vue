<!-- 
SIGNUP PAGE - form users see when creating a new account 
-->
<template>
    <div class="signup-container">
        <div class="signup-box">
          <h2>Create a SixDegrees Account</h2>
            <form @submit.prevent="handleSignUp">
                <div class="form-group">
                    <label>Nickname</label>
                    <input
                        v-model="nickname"
                        type="text"
                        @focus="showValidation = true"
                        @blur="showValidation = ~uniqueUser"
                        @input="checkNickname();"
                        placeholder="Create nickname"
                        required
                    />
                  <div v-if="showValidation" class="checklist" aria-live="polite">
                    <ul>
                      <li :class="{valid: uniqueUser && validName, invalid: !uniqueUser || !validName}">
                        <span class="dot">{{ !validName ? '✕' : (uniqueUser ? '✓' : '✕') }}</span>
                        {{ !validName ? 'Enter a valid nickname' : (uniqueUser ? 'Nickname is available' : 'Nickname is not available') }}
                      </li>
                    </ul>
                  </div>
                </div>

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
                  <div v-if="showChecklist" class="checklist" aria-live="polite">
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
const nickname = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const uniqueUser = ref(false)
const showValidation = ref(false)
const showChecklist = ref(false)

// Validates nickname format: alphanumeric and underscores only, max 35 characters
const validName = computed(() => {
  const nick = nickname.value || ''
  return /^[A-Za-z0-9_]{1,35}$/.test(nick)
})

// Checks if typed nickname is available in the db and updates the validation indicator
async function checkNickname() {
  try {
    const { data, NicknameError } = await supabase.rpc('nickname_available', {
      nickname: nickname.value
    })
    if (NicknameError) { 
      error.value = NicknameError;
      return;
    }

    uniqueUser.value = data;
    if (showValidation.value != uniqueUser.value)
      showValidation.value = true;
  } catch (err) {
    console.err(error.message);
  }
}

// Checks pw against all requirements (length, upper, lower, number, special character)
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

// Validates the password, then signs the user up with Supabase and redirects to the profile setup
async function handleSignUp() {
  if (!Object.values(validations.value).every(Boolean)) {
    error.value = 'Password does not meet the requirements.'
    return
  }

  error.value = ''

  const { data, error: signUpError } = await supabase.auth.signUp({
    email: email.value,
    password: password.value,
    options : {
      data :{
        nickname: nickname.value,
      },
    },
  })

  if (signUpError) {
    error.value = signUpError.message
    return
  }

  alert("Signup successful! You can now set up your profile.")
  router.push("/profile-setup")
}

// Redirects back to the login page
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

.checklist {
  margin-top: 0.5rem;
}
.checklist ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.checklist li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #cfcfcf;
  margin-bottom: 0.4rem;
}
.checklist li .dot {
  display: inline-block;
  width: 1.2rem;
  text-align: center;
  font-weight: 700;
}
.checklist li.valid {
  color: #8ef0a6;
}
.checklist li.invalid {
  color: #fa7676;
  opacity: 0.75;
}
</style>