<script setup lang="ts">
import { ref } from "vue";
import { fetchAuthSession, getCurrentUser, signIn, signOut } from "@aws-amplify/auth";
import { useRouter } from "vue-router";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import Message from "primevue/message";
import { Amplify } from "aws-amplify";

const router = useRouter();
const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

const handleSignIn = async () => {
  loading.value = true;
  error.value = "";

  // Validate inputs before attempting sign in
  if (!username.value || !password.value) {
    error.value = "Please enter both username and password";
    loading.value = false;
    return;
  }

  try {
    try {
      await getCurrentUser();
      await signOut();
    } catch {
    }
    // Updated to use new signIn syntax
    const output = await signIn({
      username: username.value,
      password: password.value,
      options: {
        authFlowType: "USER_PASSWORD_AUTH",
      },
    });

    router.push("/chat");
  } catch (err: any) {
    // Handle specific AWS Cognito error cases
    if (err.code === "UserNotFoundException") {
      error.value = "User does not exist";
    } else if (err.code === "NotAuthorizedException") {
      error.value = "Incorrect username or password";
    } else if (err.code === "UserNotConfirmedException") {
      error.value = "Please verify your email first";
    } else {
      error.value = err.message || "Failed to sign in";
    }
  } finally {

    loading.value = false;
  }

};
</script>
<template>
  <div class="login-page">
    <div class="login-box">
      <div class="logo-container">
        <img src="@/assets/ava.png" alt="Ava Logo" class="ava-logo" />
      </div>
      <h2>NLM WHR AI Virtual Assistant Login</h2>

      <div class="form-group">
        <FloatLabel variant="on">
          <InputText id="username" v-model="username" @keyup.enter="handleSignIn" :disabled="loading" />
          <label for="username">Username</label>
        </FloatLabel>
      </div>

      <div class="form-group">
        <FloatLabel variant="on">
          <Password id="password" v-model="password" @keyup.enter="handleSignIn" :feedback="false" :toggleMask="true"
            :disabled="loading" />
          <label for="password">Password</label>
        </FloatLabel>
      </div>

      <Message severity="error" v-if="error">{{ error }}</Message>

      <Button :label="loading ? 'Loading...' : 'Login'" @click="handleSignIn" :disabled="loading" :loading="loading" />
    </div>
  </div>
</template>

<style scoped>
/* Reset styles to ensure full coverage */
:root,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
}

.login-page {
  min-height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--surface-ground);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.login-box {
  position: relative;
  background: rgba(191, 253, 240, 0.1);
  padding: 4rem 3rem;
  /* Increased padding */
  border-radius: 12px;
  /* Slightly larger border radius */
  box-shadow: 0 0 50px rgba(0, 0, 0, 0.295);
  width: 100%;
  max-width: 600px;
  /* Increased from 400px */
  min-height: 400px;
  /* Added minimum height */
}

.logo-container {
  position: absolute;
  top: -40px;
  /* Adjusted for larger logo */
  left: 50%;
  transform: translateX(-20%);
  z-index: 1;
}


.logo-container {
  position: absolute;
  top: -50px;
  /* Adjust based on your logo size */
  left: 50%;
  transform: translateX(-50%);
  z-index: 1;
}

.ava-logo {
  width: 80px;
  /* Adjust size as needed */
  height: 80px;
  /* Adjust size as needed */
  object-fit: contain;
}

.form-group {
  margin-bottom: 2rem;
}

.form-group .p-float-label {
  width: 100%;
}

.form-group input {
  width: 100%;
  font-size: 1.1rem;
  padding: 1.2rem;
}

:deep(.p-password) {
  width: 100%;
}

:deep(.p-password-input) {
  width: 100%;
  font-size: 1.1rem;
  padding: 1.2rem;
}

:deep(.p-float-label label) {
  font-size: 1.1rem;
}

.p-button {
  width: 100%;
  margin-top: 1.5rem;
  font-size: 1.2rem;
  padding: 1rem;
}

.p-message {
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
}

.login-box h2 {
  text-align: center;
  margin: 0 0 2rem 0;
  /* Add some margin below the header */
  font-size: 2rem;
  /* Adjust font size if needed */
}

/* Responsive adjustments */
@media screen and (max-width: 576px) {
  .login-box {
    margin: 1rem;
    padding: 2rem;
  }

}
</style>
