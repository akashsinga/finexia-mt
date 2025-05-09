module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
    es2022: true,
  },
  extends: [
    'plugin:vue/vue3-recommended',
    'eslint:recommended',
  ],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  rules: {
    'vue/multi-word-component-names': 'off', // Allow single-word component names
    'vue/require-default-prop': 'off', // Don't require default values for props
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'vue/attribute-hyphenation': 'off', // Allow camelCase attributes
    'vue/v-on-event-hyphenation': 'off', // Allow camelCase event names
  },
}