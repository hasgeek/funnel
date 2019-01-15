const OFF = 0, WARN = 1, ERROR = 2;
module.exports = {
  parser: "babel-eslint",
  env: {
    "browser" : true,
    "es6": true,
    "jquery": true
  },
  extends: 'airbnb-base',
  // add your custom rules here
  'rules': {
    'no-console': OFF,
    'prefer-arrow-callback' : [ ERROR , { "allowNamedFunctions": true }],
    'prefer-const': WARN,
    'object-curly-newline': [ERROR, {
      'ObjectExpression': "always",
      'ObjectPattern': { "multiline": true }
    }],
    'new-cap': WARN,
    'no-param-reassign' : [ERROR, { "props": false }],
    'max-len' : WARN,
    // allow debugger during development
    'no-debugger': process.env.NODE_ENV === 'production' ? ERROR : OFF
  }
}