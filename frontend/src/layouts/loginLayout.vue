<!-- src/layouts/LoginLayout.vue -->
<template>
  <div class="auth-container">
    <!-- Left Panel (Logo + Decoration) -->
    <div class="auth-brand-panel">
      <div class="brand-content">
        <div class="brand-logo">
          <!-- <img src="@/assets/logo-white.svg" alt="Finexia" class="h-12"> -->
        </div>

        <div class="brand-tagline">
          <h1>Stock Market Intelligence</h1>
          <p>Advanced analytics and AI-powered predictions for financial markets</p>
        </div>

        <div class="brand-decoration">
          <div class="decoration-item animate-float"></div>
          <div class="decoration-item animate-float-delay-1"></div>
          <div class="decoration-item animate-float-delay-2"></div>
          <div class="decoration-item animate-float-delay-3"></div>
          <div class="decoration-item animate-float-delay-4"></div>
        </div>

        <div class="brand-features">
          <div class="feature-item">
            <i class="ri-line-chart-line"></i>
            <span>Market data insights</span>
          </div>
          <div class="feature-item">
            <i class="ri-ai-generate"></i>
            <span>AI-driven predictions</span>
          </div>
          <div class="feature-item">
            <i class="ri-notification-4-line"></i>
            <span>Real-time alerts</span>
          </div>
        </div>
      </div>

      <div class="brand-footer">
        <p>&copy; 2025 Finexia. All rights reserved.</p>
      </div>
    </div>

    <!-- Right Panel (Form) -->
    <div class="auth-form-panel">
      <div class="form-panel-container">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginLayout'
}
</script>

<style lang="postcss" scoped>
.brand-content {
  @apply z-10 flex flex-col space-y-16;
}

.brand-logo {
  @apply mb-8;
}

.brand-tagline {
  @apply space-y-2;
}

.brand-tagline h1 {
  @apply text-3xl font-bold text-white m-0;
}

.brand-tagline p {
  @apply text-primary-100 text-lg max-w-md;
}

.brand-decoration {
  @apply absolute inset-0 opacity-10 overflow-hidden;
}

.decoration-item {
  @apply absolute bg-white rounded-full;
}

.decoration-item:nth-child(1) {
  @apply h-64 w-64 -top-20 -right-20 opacity-20;
}

.decoration-item:nth-child(2) {
  @apply h-96 w-96 bottom-10 -left-40 opacity-10;
}

.decoration-item:nth-child(3) {
  @apply h-40 w-40 top-1/3 right-10 opacity-15;
}

.decoration-item:nth-child(4) {
  @apply h-20 w-20 bottom-40 left-20 opacity-20;
}

.decoration-item:nth-child(5) {
  @apply h-80 w-80 -top-40 -left-20 opacity-10;
}

.brand-features {
  @apply space-y-5 mt-auto;
}

.feature-item {
  @apply flex items-center space-x-3 text-primary-100;
}

.feature-item i {
  @apply text-xl;
}

.brand-footer {
  @apply text-sm text-primary-200 z-10;
}

.form-panel-container {
  @apply w-full max-w-md;
}

/* Responsive adjustments */
@media (max-width: 1023px) {
  .auth-form-panel {
    @apply bg-gray-50;
  }
}
</style>