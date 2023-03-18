import Vue from 'vue/dist/vue.esm';
import jsonForm from './utils/jsonform';

Vue.config.devtools = true;

const FormUI = {
  init(jsonSchema) {
    /* eslint-disable no-new */
    new Vue({
      el: '#register-form',
      data() {
        return {
          jsonSchema,
        };
      },
      components: {
        jsonForm,
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
  window.Hasgeek.registerForm = (jsonSchema) => {
    FormUI.init(jsonSchema);
  };
});
