<template>
  <div class="setup-container">
    <div class="setup-box">
      <h2>Complete Your Profile</h2>
      <br />
      <p>Tell us a bit about yourself to get better matches.</p>
      <br />
      <form @submit.prevent="handleSubmit">
        
        <div class="form-row">
          <div class="form-group">
            <label>City</label>
            <input v-model="form.city" type="text" placeholder="e.g. New York" required />
          </div>
          <div class="form-group">
            <label>State</label>
            <input v-model="form.state" type="text" placeholder="e.g. NY" required />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Age</label>
            <input v-model="form.age" type="number" min="15" max="100" required />
          </div>
          <div class="form-group">
            <label>Education (School)</label>
            <input v-model="form.education" type="text" placeholder="University of ..." required />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Occupation</label>
            <input v-model="form.occupation" type="text" placeholder="e.g. Software Engineer" required />
          </div>
          <div class="form-group">
            <label>Industry</label>
            <input v-model="form.industry" type="text" placeholder="e.g. Tech" required />
          </div>
        </div>

        <div class="form-group">
          <label>Interests (separate with commas)</label>
          <input 
            v-model="interestsInput" 
            type="text" 
            placeholder="e.g. Coding, Basketball, Jazz" 
          />
          <small>Type tags separated by commas</small>
        </div>

        <div class="form-group">
          <label>Languages Spoken</label>
          <input 
            v-model="languagesInput" 
            type="text" 
            placeholder="e.g. English, Mandarin, Spanish" 
          />
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <button type="submit" class="save-btn">Complete Setup</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { supabase } from "../lib/supabase";
import { useRouter } from "vue-router";

const router = useRouter();
const error = ref("");

const interestsInput = ref("");
const languagesInput = ref("");

const form = ref({
  city: "",
  state: "",
  age: null,
  education: "",
  occupation: "",
  industry: ""
});

const handleSubmit = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("Not logged in");

    const interestsArray = interestsInput.value
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);

    const languagesArray = languagesInput.value
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);

    const { error: upsertError } = await supabase
      .from("profiles")
      .upsert({
        id: user.id,
        city: form.value.city,
        state: form.value.state,
        age: parseInt(form.value.age),
        education: form.value.education,
        occupation: form.value.occupation,
        industry: form.value.industry,
        interests: interestsArray,
        languages: languagesArray,
        is_onboarded: true
      });

    if (upsertError) throw upsertError;

    router.push("/");

  } catch (err) {
    error.value = err.message;
    console.error(err);
  }
};
</script>


<style scoped>
.setup-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: #1a1a1a;
  padding: 2rem;
}
.setup-box {
  background: #2d2d2d;
  padding: 2rem;
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
  color: white;
}
.form-row {
  display: flex;
  gap: 1rem;
}
.form-group {
  margin-bottom: 1rem;
  flex: 1;
}
label {
  display: block;
  margin-bottom: 0.5rem;
  color: #b0b0b0;
}
input {
  width: 100%;
  padding: 0.75rem;
  background: #1a1a1a;
  border: 1px solid #444;
  color: white;
  border-radius: 4px;
}
.save-btn {
  width: 100%;
  padding: 1rem;
  background: #088F8F;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  margin-top: 1rem;
}
.error {
  color: #ff6b6b;
  margin-top: 1rem;
}
small {
    color: #666;
    font-size: 0.8rem;
}
</style>