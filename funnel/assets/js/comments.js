import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import * as timeago from 'timeago.js';
import { Utils } from './util';
import { userAvatarUI, faSvg } from './vue_util';

const Comments = {
  init({
    newCommentUrl,
    divElem,
    commentTemplate,
    isuserloggedin,
    isuserparticipant,
    user,
    loginUrl,
    headerHeight,
  }) {
    Vue.use(VS2);

    const commentUI = Vue.component('comment', {
      template: commentTemplate,
      props: ['comment', 'isuserparticipant'],
      data() {
        return {
          commentForm: '',
          errorMsg: '',
          svgIconUrl: window.Hasgeek.config.svgIconUrl,
          hide: false,
          now: new Date(),
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
        created_at_age() {
          return this.now && this.comment.created_at
            ? timeago.format(this.comment.created_at)
            : '';
        },
        edited_at_age() {
          return this.now && this.comment.edited_at
            ? timeago.format(this.comment.edited_at)
            : '';
        },
      },
      mounted() {
        window.setInterval(() => {
          this.now = new Date();
        }, 20000);
      },
    });

    const app = new Vue({
      el: divElem,
      components: {
        commentUI,
        userAvatarUI,
        faSvg,
      },
      data() {
        return {
          newCommentUrl,
          comments: [],
          isuserloggedin,
          isuserparticipant,
          user,
          commentForm: '',
          errorMsg: '',
          loginUrl,
          refreshInterval: window.Hasgeek.config.ajaxTimeout,
          refreshTimer: '',
          headerHeight,
          svgIconUrl: window.Hasgeek.config.svgIconUrl,
          initialLoad: true,
        };
      },
      methods: {
        fetchForm(event, url, comment = '') {
          event.preventDefault();
          if (this.isuserparticipant) {
            $.ajax({
              type: 'GET',
              url,
              timeout: window.Hasgeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                app.pauseRefreshComments();
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
          $.ajax({
            type: 'GET',
            timeout: window.Hasgeek.config.ajaxTimeout,
            dataType: 'json',
            success(data) {
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
          clearTimeout(this.refreshTimer);
        },
        refreshCommentsTimer() {
          this.refreshTimer = window.setInterval(
            this.fetchCommentsList,
            this.refreshInterval
          );
        },
        getInitials: window.Baseframe.Utils.getInitials,
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
        this.fetchCommentsList();
        this.refreshCommentsTimer();
      },
      updated() {
        if (this.initialLoad && window.location.hash) {
          Utils.animateScrollTo(
            document
              .getElementById(window.location.hash)
              .getBoundingClientRect().top - this.headerHeight
          );
          this.initialLoad = false;
        }
      },
    });
  },
};

$(() => {
  window.Hasgeek.Comments = function (config) {
    Comments.init(config);
  };
});
