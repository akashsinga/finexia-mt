// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/layouts/defaultLayout.vue';

// Lazy-load all views
const Login = () => import('@/views/auth/Login.vue');
const Dashboard = () => import('@/views/dashboard/Dashboard.vue');
// const SymbolsList = () => import('@/views/symbols/SymbolsList.vue');
// const SymbolDetail = () => import('@/views/symbols/SymbolDetail.vue');
// const PredictionsList = () => import('@/views/predictions/PredictionsList.vue');
// const Analytics = () => import('@/views/analytics/Analytics.vue');
// const SystemSettings = () => import('@/views/system/SystemSettings.vue');
// const NotFound = () => import('@/views/errors/NotFound.vue');

const routes = [
  { path: '/login', name: 'login', component: Login, meta: { title: 'Login', requiresAuth: false } },

  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: Dashboard, meta: { title: 'Dashboard', icon: 'dashboard' } },
      // { path: 'symbols', name: 'symbols', component: SymbolsList, meta: { title: 'Symbols', icon: 'trending_up' } },
      // { path: 'symbols/:id', name: 'symbol-detail', component: SymbolDetail, meta: { title: 'Symbol Details', hideInMenu: true }, props: true },
      // { path: 'predictions', name: 'predictions', component: PredictionsList, meta: { title: 'Predictions', icon: 'insights' } },
      // { path: 'analytics', name: 'analytics', component: Analytics, meta: { title: 'Analytics', icon: 'assessment' } },
      // { path: 'settings', name: 'settings', component: SystemSettings, meta: { title: 'System Settings', icon: 'settings', requiresAdmin: true } }
    ]
  },

  // { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFound, meta: { title: 'Page Not Found' } }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to, from, savedPosition) => savedPosition || { top: 0 }
});

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'Finexia'} | Stock Market Intelligence`;

  const requiresAuth = to.matched.some(record => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);
  const isAuthenticated = !!localStorage.getItem('token');
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  if (requiresAuth && !isAuthenticated)
    next({ name: 'login', query: { redirect: to.fullPath } });
  else if (requiresAdmin && !user.is_admin)
    next({ name: 'dashboard' });
  else if (to.path === '/login' && isAuthenticated)
    next({ name: 'dashboard' });
  else next();
});

export default router;