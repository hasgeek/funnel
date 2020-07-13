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
    headerHeight,
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
        fetchForm(event, url, comment) {
          if (comment) {
            this.$parent.fetchForm(event, url, comment);
          } else {
            this.$parent.fetchForm(event, url, this);
          }
        },
        updateCommentsList(commentsList) {
          this.$parent.updateCommentsList(commentsList);
        },
        activateForm(comment) {
          this.$parent.activateForm(comment);
        },
        refreshCommentsTimer() {
          this.$parent.refreshCommentsTimer();
        },
        closeForm(event) {
          event.preventDefault();
          this.commentForm = '';
          this.errorMsg = '';
          this.$parent.refreshCommentsTimer();
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
          loginUrl,
          refreshInterval: 30000,
          refreshTimer: '',
          headerHeight,
          svgIconUrl: window.HasGeek.config.svgIconUrl,
        };
      },
      methods: {
        fetchForm(event, url, comment = '') {
          event.preventDefault();
          if (this.isuserparticipant) {
            $.ajax({
              type: 'GET',
              url,
              timeout: window.HasGeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                app.pauseRefreshComments();
                console.log('data', data);
                const vueFormHtml = data.form;
                if (comment) {
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
          const formId = Utils.getElementId(parentApp.commentForm);
          const url = Utils.getActionUrl(formId);
          const onSuccess = (responseData) => {
            parentApp.commentForm = '';
            parentApp.errorMsg = '';
            if (responseData.comments) {
              parentApp.updateCommentsList(responseData.comments);
              window.toastr.success(responseData.message);
            }
            app.refreshCommentsTimer();
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
        fetchCommentsList() {
          console.log('fetchCommentsList');
          $.ajax({
            type: 'GET',
            timeout: window.HasGeek.config.ajaxTimeout,
            dataType: 'json',
            success(data) {
              console.log('fetchCommentsList data', data);
              app.updateCommentsList(data.comments);
            },
          });
        },
        closeForm(event) {
          event.preventDefault();
          this.commentForm = '';
          this.errorMsg = '';
          this.refreshCommentsTimer();
        },
        pauseRefreshComments() {
          console.log('clear timer');
          clearTimeout(this.refreshTimer);
        },
        refreshCommentsTimer() {
          console.log('started timer');
          this.refreshTimer = window.setInterval(
            this.fetchCommentsList,
            this.refreshInterval
          );
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
      mounted() {
        this.refreshCommentsTimer();
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
  window.HasGeek.Comments = function (config) {
    Comments.init(config);
  };
});
