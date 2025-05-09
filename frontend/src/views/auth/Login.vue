<!-- src/views/auth/Login.vue -->
<template>
  <LoginLayout>
    <div class="login-form-wrapper slide-in-up">
      <div class="login-header">
        <h2>Welcome back</h2>
        <p>Sign in to your account to continue</p>
      </div>

      <div v-if="error" class="alert-error">
        <i class="ph ph-warning-circle"></i>
        <span>{{ error }}</span>
        <button @click="clearError" class="alert-close">
          <i class="ph ph-x"></i>
        </button>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username" class="form-label">Username</label>
          <div class="input-wrapper">
            <i class="ph ph-user input-icon"></i>
            <input type="text" id="username" v-model="username" class="form-input with-icon" placeholder="Enter your username" :disabled="loading" required autocomplete="username" />
          </div>
        </div>

        <div class="form-group">
          <div class="password-header">
            <label for="password" class="form-label">Password</label>
            <a href="#" class="text-sm">Forgot password?</a>
          </div>
          <div class="input-wrapper">
            <i class="ph ph-lock input-icon"></i>
            <input :type="showPassword ? 'text' : 'password'" id="password" v-model="password" class="form-input with-icon" placeholder="Enter your password" :disabled="loading" required autocomplete="current-password" />
            <button type="button" @click="showPassword = !showPassword" class="input-action" tabindex="-1">
              <i :class="showPassword ? 'ph ph-eye-slash' : 'ph ph-eye'"></i>
            </button>
          </div>
        </div>

        <div class="remember-me">
          <label class="checkbox-container">
            <input type="checkbox" v-model="rememberMe" :disabled="loading">
            <span class="checkmark"></span>
            <span>Remember me</span>
          </label>
        </div>

        <button type="submit" class="btn-login" :disabled="loading || !username || !password">
          <span v-if="!loading">Sign in</span>
          <div v-else class="spinner-light"></div>
        </button>
      </form>

      <div class="login-footer">
        <p>Don't have an account? <a href="#">Contact your administrator</a></p>
      </div>
    </div>
  </LoginLayout>
</template>

<script>
import { useAuthStore } from '@/stores/auth';
import LoginLayout from '@/layouts/loginLayout.vue';

export default {
  name: 'LoginPage',

  components: {
    LoginLayout
  },

  data: function () {
    return {
      username: '',
      password: '',
      rememberMe: false,
      showPassword: false,
      loading: false,
      error: ''
    };
  },

  computed: {
    authStore: function () {
      return useAuthStore();
    }
  },

  methods: {
    handleLogin: function () {
      if (!this.username || !this.password) return;

      this.loading = true;
      this.error = '';

      setTimeout(() => {
        this.authStore.login(this.username, this.password)
          .then(() => {
            // Redirect to intended destination if available
            const redirectPath = this.$route.query.redirect || '/';
            this.$router.push(redirectPath);
          })
          .catch(err => {
            this.error = err.response?.data?.detail || 'Login failed. Please check your credentials and try again.';
          })
          .finally(() => {
            this.loading = false;
          });
      }, 1000); // Simulate server delay for better UX
    },

    clearError: function () {
      this.error = '';
    }
  }
};
</script>

<style lang="postcss" scoped>
.login-header {
  @apply text-center mb-8;
}

.login-header h2 {
  @apply text-2xl font-bold text-gray-900 mb-1;
}

.login-header p {
  @apply text-gray-500;
}

.login-form {
  @apply space-y-6;
}

.password-header {
  @apply flex justify-between items-center;
}

.password-header a {
  @apply text-indigo-600 hover:text-indigo-700 font-medium;
}

.remember-me {
  @apply flex items-center;
}

.btn-login {
  @apply w-full py-3 px-4 flex justify-center items-center text-white font-medium rounded-xl hover:bg-opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-200 disabled:opacity-70 disabled:cursor-not-allowed;
  background: var(--brand-blue);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  &:hover:not(:disabled) {
    background: #172b69;
    /* Slightly darker */
  }

  &:focus {
    @apply ring-indigo-500;
  }
}

.login-footer {
  @apply text-center text-sm text-gray-500 mt-6;
}

.login-footer a {
  @apply text-indigo-600 hover:text-indigo-700 font-medium;
}
</style>