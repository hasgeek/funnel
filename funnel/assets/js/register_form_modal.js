import Vue from 'vue/dist/vue.esm';

Vue.config.devtools = true;

const FormUI = {
  init(formFields) {
    /* eslint-disable no-new */
    new Vue({
      el: '#register-form',
      data() {
        return {
          formFields,
        };
      },
      methods: {
        onChange(event) {
          this.data = event.data;
        },
      },
      mounted() {
        console.log('mounted');
      },
    });
  },
};

$(() => {
  window.Hasgeek.registerForm = (formFields) => {
    FormUI.init(formFields);
  };
});
