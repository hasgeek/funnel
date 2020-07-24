import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import { Utils } from './util';

const Posts = {
  init({
    newPostUrl,
    posts = '',
    divElem,
    postTemplate,
    isuserloggedin,
    isEditor,
    loginUrl,
    headerHeight,
  }) {
    Vue.config.devtools = true;
    Vue.use(VS2);

    const postUI = Vue.component('post', {
      template: postTemplate,
      props: ['post'],
      data() {
        return {
          postForm: '',
          errorMsg: '',
          svgIconUrl: window.HasGeek.config.svgIconUrl,
        };
      },
      methods: {
        getInitials: window.Baseframe.Utils.getInitials,
        collapse(action) {
          this.hide = action;
        },
        fetchForm(event, url, post) {
          if (post) {
            this.$parent.fetchForm(event, url, post);
          } else {
            this.$parent.fetchForm(event, url, this);
          }
        },
        activateForm(post) {
          this.$parent.activateForm(post);
        },
        closeForm(event) {
          event.preventDefault();
          this.postForm = '';
          this.errorMsg = '';
        },
      },
      computed: {
        Form() {
          const template = this.postForm ? this.postForm : '<div></div>';
          const isFormTemplate = this.postForm ? true : '';
          return {
            template,
            mounted() {
              if (isFormTemplate) {
                this.$parent.activateForm(this.$parent);
              }
            },
          };
        },
      },
    });

    const app = new Vue({
      el: divElem,
      components: {
        postUI,
      },
      data() {
        return {
          newPostUrl,
          posts: posts.length > 0 ? posts : '',
          isuserloggedin,
          isEditor,
          postForm: '',
          errorMsg: '',
          loginUrl,
          headerHeight,
          svgIconUrl: window.HasGeek.config.svgIconUrl,
        };
      },
      methods: {
        fetchForm(event, url, post = '') {
          event.preventDefault();
          if (this.isEditor) {
            $.ajax({
              type: 'GET',
              url,
              timeout: window.HasGeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                console.log('data', data);
                const vueFormHtml = data.form;
                if (post) {
                  post.postForm = vueFormHtml.replace(/\bscript\b/g, 'script2');
                } else {
                  app.postForm = vueFormHtml.replace(/\bscript\b/g, 'script2');
                }
              },
            });
          }
        },
        activateForm(parentApp) {
          const formId = Utils.getElementId(parentApp.postForm);
          const url = Utils.getActionUrl(formId);
          const onSuccess = (responseData) => {
            window.location.href = responseData.new_post_url;
          };
          const onError = (response) => {
            parentApp.errorMsg = Utils.formErrorHandler(formId, response);
          };
          window.Baseframe.Forms.handleFormSubmit(
            formId,
            url,
            onSuccess,
            onError,
            {}
          );
        },
        closeForm(event) {
          event.preventDefault();
          this.postForm = '';
          this.errorMsg = 'Posts';
        },
      },
      computed: {
        Form() {
          const template = this.postForm ? this.postForm : '<div></div>';
          const isFormTemplate = this.postForm ? true : '';
          return {
            template,
            mounted() {
              if (isFormTemplate) {
                this.$parent.activateForm(this.$parent);
              }
            },
          };
        },
      },
      mounted() {
        if (window.location.hash) {
          Utils.animateScrollTo(
            document
              .getElementById(window.location.hash)
              .getBoundingClientRect().top - this.headerHeight
          );
        }
      },
    });
  },
};

$(() => {
  window.HasGeek.PostsInit = function (config) {
    Posts.init(config);
  };
});
