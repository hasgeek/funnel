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
        handleAjaxPost() {
          window.location.hash = '';
          window.location.reload();
        },
      },
    });
  },
};

$(() => {
  window.Hasgeek.addRsvpForm = (jsonSchema) => {
    FormUI.init(jsonSchema);
  };
});
