import Vue from 'vue/dist/vue.min';
import Form from './formhelper';

const jsonForm = Vue.component('jsonform', {
  template: '#form-template',
  props: ['jsonschema', 'title', 'formid'],
  methods: {
    getFormData() {
      const obj = {};
      const formData = $(`#${this.formid}`).serializeArray();
      formData.forEach((field) => {
        obj[field.name] = field.value;
      });
      return JSON.stringify(obj);
    },
    activateForm() {
      const form = this;
      const url = Form.getActionUrl(this.formid);
      const onError = (response) => {
        Form.formErrorHandler(this.formid, response);
      };
      $(`#${this.formid}`)
        .find('button[type="submit"]')
        .click((event) => {
          event.preventDefault();
          window.Hasgeek.Forms.ajaxFormSubmit(this.formid, url, '', onError, {
            contentType: 'application/json',
            formData: JSON.stringify({ form: form.getFormData() }),
          });
        });
    },
  },
  mounted() {
    this.activateForm();
  },
});

export default jsonForm;
