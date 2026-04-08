<template>
  <div class="setup-container">
    <div class="setup-box">
      <h2>Complete Your Profile</h2>
      <br />
      <p>Tell us a bit about yourself to get better matches.</p>
      <br />
      <form @submit.prevent="handleSubmit">
        
        <div class="form-group avatar-upload-group">
          <label>Profile Photo (optional)</label>
          <div class="avatar-preview" @click="triggerUpload">
            <img v-if="avatarPreview" :src="avatarPreview" class="avatar-preview-img" />
            <div v-else class="avatar-placeholder">+</div>
            <input ref="fileInput" type="file" accept="image/*" hidden @change="handleAvatarChange" />
          </div>
          <small>Click to upload a photo</small>
        </div>

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

const fileInput = ref(null)
const avatarFile = ref(null)
const avatarPreview = ref(null)

const form = ref({
  city: "",
  state: "",
  age: null,
  education: "",
  occupation: "",
  industry: ""
});

/*
  Handles profile setup form submission:
  - Parses comma-separated interests and languages
  - Uploads avatar if provided
  - Creates profile and redirects to the home feed
*/
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

    let uploadedAvatarUrl = null

    if(avatarFile.value){
      const ext = avatarFile.value.name.split('.').pop()
      const path = `${user.id}/avatar.${ext}`

      const { error: uploadError } = await supabase.storage
        .from('avatars')
        .upload(path, avatarFile.value, { upsert: true })
      if(uploadError) throw uploadError

      const { data: { publicUrl } } = supabase.storage
        .from('avatars')
        .getPublicUrl(path)

      uploadedAvatarUrl = publicUrl
    }

    const { error: profileError } = await supabase.rpc('create_profile', {
        bio: '',
        age: parseInt(form.value.age),
        city: form.value.city,
        state: form.value.state,
        education: form.value.education,
        occupation: form.value.occupation,
        industry: form.value.industry,
        interests: interestsArray,
        languages: languagesArray,
        profile_tier: 6, //visible to everyone, can change later
        avatar_url: uploadedAvatarUrl
    });

    if (profileError) throw profileError;

    router.push("/");

  } catch (err) {
    error.value = err.message;
    console.error(err);
  }
};

// Programatically triggers the hidden file input for avatar upload
function triggerUpload() {
  fileInput.value.click()
}

// Validates the selected image, stores it locally, and shows a preview
function handleAvatarChange(event) {
  const file = event.target.files[0]
  if (!file) return
  const ALLOWED = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!ALLOWED.includes(file.type)) { error.value = 'Only JPEG, PNG, GIF, or WebP allowed'; return }
  if (file.size > 2 * 1024 * 1024) { error.value = 'Max file size is 2MB'; return }
  if (avatarPreview.value) URL.revokeObjectURL(avatarPreview.value)
  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}
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
.avatar-upload-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 1rem;
}

.avatar-preview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: #1a1a1a;
  border: 2px dashed #444;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.2s;
}

.avatar-preview:hover {
  border-color: #088F8F;
}

.avatar-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.avatar-placeholder {
  font-size: 2rem;
  color: #444;
}
</style>