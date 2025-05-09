<!-- src/layouts/LoginLayout.vue -->
<template>
  <div class="auth-container">
    <!-- Left Panel (Logo + Content) -->
    <div class="auth-brand-panel">
      <div class="brand-content">
        <div class="brand-logo-container">
          <!-- Logo section with new styling -->
          <div class="brand-logo-wrapper">
            <img src="@/assets/images/favicon.svg" alt="Finexia" class="logo">
            <div class="brand-identity">
              <h1 class="brand-name">FINEXIA</h1>
              <div class="tagline-divider"></div>
              <p class="brand-tagline">PREDICTIVE MARKET ANALYTICS</p>
            </div>
          </div>
        </div>

        <div class="hero-content">
          <h2 class="hero-title">Trading Insights Powered by AI</h2>
          <p class="hero-description">Predict market movements with precision using our advanced machine learning models.</p>

          <div class="stats-container">
            <div class="stat-item">
              <div class="stat-value">87<span class="text-green-300">%</span></div>
              <div class="stat-label">Prediction Accuracy</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">10K<span class="text-green-300">+</span></div>
              <div class="stat-label">Data Points Analyzed</div>
            </div>
          </div>
        </div>

        <div class="feature-showcase">
          <div class="feature-item">
            <div class="feature-icon">
              <i class="ph ph-trend-up"></i>
            </div>
            <div class="feature-text">
              <h3>Predictive Analytics</h3>
              <p>Forecast potential market movements with our AI-driven models</p>
            </div>
          </div>

          <div class="feature-item">
            <div class="feature-icon">
              <i class="ph ph-chart-line"></i>
            </div>
            <div class="feature-text">
              <h3>Real-Time Monitoring</h3>
              <p>Track market fluctuations with live data updates</p>
            </div>
          </div>

          <div class="feature-item">
            <div class="feature-icon">
              <i class="ph ph-bell-ringing"></i>
            </div>
            <div class="feature-text">
              <h3>Smart Alerts</h3>
              <p>Receive notifications when significant market movements are predicted</p>
            </div>
          </div>
        </div>

        <!-- Animated decoration elements -->
        <div class="brand-decoration">
          <div class="decoration-item animate-float"></div>
          <div class="decoration-item animate-float-delay-1"></div>
          <div class="decoration-item animate-float-delay-2"></div>
          <div class="chart-decoration">
            <!-- Stylized uptrend -->
            <svg width="300" height="120" viewBox="0 0 300 120" class="uptrend-decoration">
              <path d="M0,100 L50,80 L100,85 L150,65 L200,55 L250,35 L300,20" stroke="rgba(74, 222, 128, 0.2)" stroke-width="3" fill="none" />
              <circle cx="50" cy="80" r="4" fill="rgba(74, 222, 128, 0.3)" />
              <circle cx="100" cy="85" r="4" fill="rgba(74, 222, 128, 0.3)" />
              <circle cx="150" cy="65" r="4" fill="rgba(74, 222, 128, 0.3)" />
              <circle cx="200" cy="55" r="4" fill="rgba(74, 222, 128, 0.3)" />
              <circle cx="250" cy="35" r="4" fill="rgba(74, 222, 128, 0.3)" />
              <circle cx="300" cy="20" r="6" fill="rgba(74, 222, 128, 0.5)" />
            </svg>

            <!-- Stylized downtrend -->
            <svg width="300" height="120" viewBox="0 0 300 120" class="downtrend-decoration">
              <path d="M0,20 L50,40 L100,35 L150,50 L200,65 L250,75 L300,100" stroke="rgba(239, 68, 68, 0.2)" stroke-width="3" fill="none" />
              <circle cx="50" cy="40" r="4" fill="rgba(239, 68, 68, 0.3)" />
              <circle cx="100" cy="35" r="4" fill="rgba(239, 68, 68, 0.3)" />
              <circle cx="150" cy="50" r="4" fill="rgba(239, 68, 68, 0.3)" />
              <circle cx="200" cy="65" r="4" fill="rgba(239, 68, 68, 0.3)" />
              <circle cx="250" cy="75" r="4" fill="rgba(239, 68, 68, 0.3)" />
              <circle cx="300" cy="100" r="6" fill="rgba(239, 68, 68, 0.5)" />
            </svg>
          </div>
        </div>
      </div>

      <div class="brand-footer">
        <p>&copy; 2025 Finexia. All rights reserved.</p>
        <div class="brand-social">
          <a href="#" class="social-icon"><i class="ph ph-twitter-logo"></i></a>
          <a href="#" class="social-icon"><i class="ph ph-linkedin-logo"></i></a>
          <a href="#" class="social-icon"><i class="ph ph-facebook-logo"></i></a>
        </div>
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
  @apply z-10 flex flex-col py-4;
}

/* New branded logo section styling */
.brand-logo-container {
  @apply mb-16;
}

.brand-logo-wrapper {
  @apply inline-flex flex-col items-center w-full p-4 rounded-lg bg-blue-800 bg-opacity-30 border border-blue-700;
}

.logo {
  @apply h-16 w-16 mb-3;
}

.brand-identity {
  @apply flex flex-col items-center;
}

.brand-name {
  @apply text-2xl font-bold text-white tracking-wide m-0;
}

.tagline-divider {
  @apply w-12 h-0.5 bg-green-400 my-2.5;
}

.brand-tagline {
  @apply text-xs font-medium uppercase tracking-widest text-blue-200 m-0;
}

.hero-content {
  @apply mb-12;
}

.hero-title {
  @apply text-3xl font-bold text-white mb-3;
  line-height: 1.2;
}

.hero-description {
  @apply text-lg text-blue-100 max-w-md mb-8;
}

.stats-container {
  @apply grid grid-cols-2 gap-6 mb-8;
}

.stat-item {
  @apply bg-blue-900 bg-opacity-30 rounded-lg p-4 border border-blue-800;
}

.stat-value {
  @apply text-3xl font-bold text-white mb-1;
}

.stat-label {
  @apply text-sm text-blue-200;
}

.feature-showcase {
  @apply space-y-6 mb-8;
}

.feature-item {
  @apply flex items-start space-x-4;
}

.feature-icon {
  @apply flex-shrink-0 w-10 h-10 rounded-full bg-blue-800 bg-opacity-50 flex items-center justify-center text-green-400 text-xl;
}

.feature-text h3 {
  @apply text-white text-lg font-semibold mb-1;
}

.feature-text p {
  @apply text-blue-200 text-sm;
}

.brand-decoration {
  @apply absolute inset-0 overflow-hidden pointer-events-none;
}

.decoration-item {
  @apply absolute bg-white rounded-full;
}

.decoration-item:nth-child(1) {
  @apply h-64 w-64 -top-20 -right-20 opacity-5;
}

.decoration-item:nth-child(2) {
  @apply h-96 w-96 bottom-40 -left-60 opacity-5;
}

.chart-decoration {
  @apply absolute bottom-20 right-0 left-0 opacity-30 pointer-events-none;
}

.uptrend-decoration,
.downtrend-decoration {
  @apply absolute;
}

.uptrend-decoration {
  @apply bottom-12 left-0;
  animation: float 30s ease-in-out infinite;
}

.downtrend-decoration {
  @apply bottom-24 left-10;
  animation: float 25s ease-in-out infinite reverse;
  animation-delay: -5s;
}

.brand-footer {
  @apply flex justify-between items-center text-sm text-blue-200 z-10 mt-auto;
}

.brand-social {
  @apply flex space-x-4;
}

.social-icon {
  @apply text-blue-300 hover:text-white transition-colors;
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