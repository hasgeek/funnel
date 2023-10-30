import Vue from 'vue/dist/vue.esm';
import jsonForm from './utils/jsonform';

Vue.config.devtools = true;

const FormUI = {
  init(jsonSchema, useremail) {
    /* eslint-disable no-new */
    new Vue({
      el: '#register-form',
      data() {
        return {
          jsonSchema,
          useremail,
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
  window.Hasgeek.addRsvpForm = (jsonSchema, useremail) => {
    FormUI.init(jsonSchema, useremail);
  };
});
