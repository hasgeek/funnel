module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  ignorePatterns: [
    'build/*',
    'funnel/static/build/*',
    'funnel/static/gen/*',
    'funnel/static/js/libs/*',
    'funnel/static/js/*.packed.js',
  ],
  env: {
    browser: true,
    es6: true,
    jquery: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:prettier/recommended',
    'plugin:cypress/recommended',
    'plugin:@typescript-eslint/strict',
    'plugin:@typescript-eslint/stylistic',
  ],
  plugins: ['@typescript-eslint'],
  rules: {
    'no-console': 'warn',
    'prefer-arrow-callback': ['error', { allowNamedFunctions: true }],
    'prefer-const': 'warn',
    'new-cap': 'warn',
    'no-param-reassign': ['error', { props: false }],
    // allow debugger during development
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'cypress/no-unnecessary-waiting': 'off',
    '@typescript-eslint/no-this-alias': 'off',
  },
};
