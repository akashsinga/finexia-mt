<template>
  <div class="min-h-screen flex items-center justify-center relative overflow-hidden bg-gray-50 bg-pattern">
    <div class="w-full max-w-md px-4 z-10">
      <div class="bg-white rounded-xl shadow-xl p-8 ring-1 ring-gray-300">
        <!-- Logo and brand -->
        <div class="flex flex-col items-center justify-center mb-6">
          <div class="mb-3 bg-blue-800 rounded-full p-3 flex items-center justify-center">
            <img src="@/assets/images/favicon.svg" class="w-12 h-12" alt="Finexia logo" />
          </div>
          <div class="flex flex-col items-center">
            <h1 class="text-2xl font-semibold text-gray-800 mb-1">Finexia</h1>
            <p class="text-sm text-gray-500">Predictive Stock Analytics</p>
          </div>
        </div>

        <!-- Login form -->
        <form @submit.prevent="handleLogin" class="flex flex-col">
          <h2 class="text-xl font-medium text-center mb-4 text-gray-800">Welcome Back</h2>

          <!-- Error alert -->
          <div v-if="error" class="flex items-center p-3 mb-4 text-sm text-red-600 bg-red-50 rounded-md">
            <i class="ph ph-warning-circle mr-2"></i>
            <span>{{ error }}</span>
          </div>

          <!-- Username field -->
          <div class="mb-4">
            <label for="username" class="form-label">Username</label>
            <div class="form-input-icon-wrapper">
              <i class="ph ph-user input-icon"></i>
              <input id="username" v-model="username" type="text" placeholder="Enter your username" required autocomplete="username" class="form-input" />
            </div>
          </div>

          <!-- Password field -->
          <div class="mb-4">
            <div class="flex justify-between items-center">
              <label for="password" class="form-label">Password</label>
              <a href="#" class="text-xs text-blue-600 hover:text-blue-800 transition-colors duration-200">Forgot password?</a>
            </div>
            <div class="form-input-icon-wrapper">
              <i class="ph ph-lock input-icon"></i>
              <input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" placeholder="Enter your password" required autocomplete="current-password" class="form-input" />
              <button type="button" @click="showPassword = !showPassword" class="input-icon-right">
                <i class="ph" :class="showPassword ? 'ph-eye-slash' : 'ph-eye'"></i>
              </button>
            </div>
          </div>

          <!-- Remember me checkbox -->
          <div class="flex items-center mb-6">
            <label class="flex items-center text-sm text-gray-600 cursor-pointer">
              <input type="checkbox" v-model="rememberMe" class="form-checkbox" />
              <span class="ml-2">Remember me</span>
            </label>
          </div>

          <!-- Submit button -->
          <button type="submit" class="form-button" :disabled="loading">
            <i v-if="loading" class="ph ph-spinner animate-spin"></i>
            <span v-else>Sign In</span>
          </button>
        </form>

        <!-- Footer -->
        <div class="text-center mt-6 text-sm text-gray-600">
          <div class="flex items-center mb-4">
            <div class="flex-grow border-t border-gray-300"></div>
            <span class="px-3 text-xs text-gray-500">OR</span>
            <div class="flex-grow border-t border-gray-300"></div>
          </div>
          <p>Don't have an account? <a href="#" @click.prevent="goToRegister" class="text-blue-600 font-medium hover:text-blue-800 transition-colors duration-200">Sign up</a></p>
        </div>
      </div>
    </div>

    <!-- Background decorations -->
    <div class="absolute rounded-full blur-3xl opacity-20 bg-blue-600 w-[400px] h-[400px] top-[-100px] right-[-100px] z-1"></div>
    <div class="absolute rounded-full blur-3xl opacity-20 bg-blue-400 w-[300px] h-[300px] bottom-[-50px] left-[-50px] z-1"></div>
  </div>
</template>

<script>
import { useAuthStore } from '@/stores/auth'

export default {
  name: 'LoginView',
  data() {
    return {
      username: '',
      password: '',
      rememberMe: false,
      showPassword: false,
      loading: false,
      error: null
    }
  },
  methods: {
    async handleLogin() {
      if (!this.username || !this.password) return

      this.loading = true
      this.error = null

      try {
        const authStore = useAuthStore()
        await authStore.login(this.username, this.password)
        this.$router.push('/')
      } catch (err) {
        this.error = err.response?.data?.detail || 'Invalid credentials. Please try again.'
      } finally {
        this.loading = false
      }
    },
    goToRegister() {
      this.$router.push('/register')
    }
  }
}
</script>

<style>
.bg-pattern {
  background-image:
    radial-gradient(circle, rgba(30, 58, 138, 0.1) 2px, transparent 2px),
    radial-gradient(circle, rgba(14, 165, 233, 0.1) 2px, transparent 2px);
  background-size: 40px 40px;
  background-position: 0 0, 20px 20px;
}
</style>