import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import { Utils } from './util';

const Comments = {
  init({
    newCommentUrl,
    comments = '',
    divElem,
    commentTemplate,
    isuserloggedin,
    isuserparticipant,
    loginUrl,
  }) {
    Vue.config.debug = true;
    Vue.use(VS2);

    const commentUI = Vue.component('comment', {
      template: commentTemplate,
      props: ['comment', 'isuserparticipant'],
      data() {
        return {
          svgIconUrl: window.HasGeek.config.svgIconUrl,
          hide: false,
        };
      },
      methods: {
        getInitials: window.Baseframe.Utils.getInitials,
        collapse(action) {
          this.hide = action;
        },
        fetchForm(event, url, comment = '') {
          this.$parent.fetchForm(event, url, comment);
        },
      },
    });

    const app = new Vue({
      el: divElem,
      components: {
        commentUI,
      },
      data() {
        return {
          newCommentUrl,
          comments: comments.length > 0 ? comments : '',
          isuserloggedin,
          isuserparticipant,
          commentForm: '',
          activeComment: '',
          errorMsg: '',
          view: 'name',
          search: '',
          showInfo: false,
          isMobile: false,
          ready: false,
          loginUrl,
          svgIconUrl: window.HasGeek.config.svgIconUrl,
        };
      },
      methods: {
        fetchForm(event, url, comment = '') {
          console.log('fetchForm', url, comment);
          event.preventDefault();
          if (this.isuserparticipant) {
            app.activeComment = comment;
            $.ajax({
              type: 'GET',
              url,
              timeout: window.HasGeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                console.log('data', data);
                const vueFormHtml = data.form;
                app.commentForm = vueFormHtml.replace(/\bscript\b/g, 'script2');
              },
            });
          }
        },
        activateForm() {
          const formId = Utils.getElementId(app.commentForm);
          const url = Utils.getActionUrl(formId);
          const onSuccess = (responseData) => {
            app.commentForm = '';
            app.errorMsg = '';
            if (responseData.comments) {
              app.updateCommentsList(responseData.comments);
              app.onChange();
              window.toastr.success(responseData.message);
            }
          };
          const onError = (response) => {
            app.errorMsg = Utils.formErrorHandler(formId, response);
          };
          window.Baseframe.Forms.handleFormSubmit(
            formId,
            url,
            onSuccess,
            onError,
            {}
          );
        },
        updateCommentsList(commentsList) {
          app.comments = commentsList.length > 0 ? commentsList : '';
        },
      },
      computed: {
        Form() {
          const template = this.commentForm ? this.commentForm : '<div></div>';
          const isFormTemplate = this.commentForm ? true : '';
          return {
            template,
            mounted() {
              if (isFormTemplate) {
                this.$parent.activateForm();
              }
            },
          };
        },
      },
      mounted() {},
      created() {
        console.log('vue is created', comments);
      },
    });
  },
};

$(() => {
  window.HasGeek.Comments = function (config) {
    Comments.init(config);
  };
});
