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
        handleAjaxPost(formId, ajaxResponse) {
          $(`#${formId}`).html(ajaxResponse);
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
