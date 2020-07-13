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
    Vue.config.devtools = true;
    Vue.use(VS2);

    const commentUI = Vue.component('comment', {
      template: commentTemplate,
      props: ['comment', 'isuserparticipant'],
      data() {
        return {
          commentForm: '',
          errorMsg: '',
          svgIconUrl: window.HasGeek.config.svgIconUrl,
          hide: false,
        };
      },
      methods: {
        getInitials: window.Baseframe.Utils.getInitials,
        collapse(action) {
          this.hide = action;
        },
        fetchForm(event, url) {
          this.$parent.fetchForm(event, url, this);
        },
        updateCommentsList(commentsList) {
          this.$parent.updateCommentsList(commentsList);
        },
        activateForm() {
          this.$parent.activateForm(this);
        },
        closeForm(event) {
          event.preventDefault();
          this.commentForm = '';
          this.errorMsg = '';
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
            $.ajax({
              type: 'GET',
              url,
              timeout: window.HasGeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                console.log('data', data);
                const vueFormHtml = data.form;
                if (comment) {
                  console.log('comment', comment);
                  comment.commentForm = vueFormHtml.replace(
                    /\bscript\b/g,
                    'script2'
                  );
                } else {
                  app.commentForm = vueFormHtml.replace(
                    /\bscript\b/g,
                    'script2'
                  );
                }
              },
            });
          }
        },
        activateForm(parentApp) {
          console.log('activateForm parentApp', parentApp);
          const formId = Utils.getElementId(parentApp.commentForm);
          const url = Utils.getActionUrl(formId);
          const onSuccess = (responseData) => {
            parentApp.commentForm = '';
            parentApp.errorMsg = '';
            if (responseData.comments) {
              parentApp.updateCommentsList(responseData.comments);
              window.toastr.success(responseData.message);
            }
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
        updateCommentsList(commentsList) {
          this.comments = commentsList.length > 0 ? commentsList : '';
        },
        closeForm(event) {
          event.preventDefault();
          this.commentForm = '';
          this.errorMsg = '';
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
                this.$parent.activateForm(this.$parent);
              }
            },
          };
        },
      },
      mounted() {},
      created() {},
    });
  },
};

$(() => {
  window.HasGeek.Comments = function (config) {
    Comments.init(config);
  };
});
