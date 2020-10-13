import Vue from 'vue/dist/vue.min';
import * as timeago from 'timeago.js';
import { Utils } from './util';
import { userAvatarUI, faSvg, shareDropdown } from './vue_util';

const Comments = {
  init({
    newCommentUrl,
    divElem,
    commentTemplate,
    isuserloggedin,
    isuserparticipant,
    iscommentmoderator,
    user,
    loginUrl,
    headerHeight,
  }) {
    Vue.config.devtools = true;

    const COMMENTACTIONS = {
      REPLY: 0,
      EDIT: 1,
      DELETE: 2,
      NEWCOMMENT: 3,
      REPORTSPAM: 4,
    };

    Vue.mixin({
      created: function () {
        this.COMMENTACTIONS = COMMENTACTIONS;
      },
    });

    const commentUI = Vue.component('comment', {
      template: commentTemplate,
      props: ['comment', 'user', 'isuserparticipant', 'iscommentmoderator'],
      data() {
        return {
          errorMsg: '',
          svgIconUrl: window.Hasgeek.config.svgIconUrl,
          reply: '',
          textarea: '',
          formAction: [
            { title: 'Reply', form: 'replyForm' },
            { title: 'Edit', form: 'editForm' },
            { title: 'Delete', form: 'deleteForm' },
            { title: 'Report spam', form: 'spamForm' },
          ],
          replyForm: false,
          editForm: false,
          deleteForm: false,
          spamForm: false,
          formOpened: false,
          commentFormTitle: '',
          hide: false,
          now: new Date(),
        };
      },
      methods: {
        getInitials: window.Baseframe.Utils.getInitials,
        collapse(action) {
          this.hide = action;
        },
        closeAllForms(event) {
          if (event) event.preventDefault();
          console.log('closeAllForms');
          this.formOpened = false;
          this.replyForm = false;
          this.editForm = false;
          this.deleteForm = false;
          this.spamForm = false;
        },
        activateSubForm(event, action, textareaId = '') {
          event.preventDefault();
          this.$root.$emit('closeCommentForms');
          this.formOpened = true;
          this.commentFormTitle = this.formAction[action].title;
          this[this.formAction[action].form] = true;
          if (action === this.COMMENTACTIONS.EDIT) {
            this.textarea = this.comment.message.text;
          }
          this.$parent.activateForm(action, textareaId, this);
        },
        activateForm(action, textareaId = '', comment) {
          this.$parent.activateForm(action, textareaId, comment);
        },
        submitCommentForm(formId, postUrl, action, comment = '') {
          if (comment) {
            this.$parent.submitCommentForm(formId, postUrl, action, comment);
          } else {
            this.$parent.submitCommentForm(formId, postUrl, action, this);
          }
        },
        handleFormSubmit(action) {
          console.log('handleFormSubmit');
          if (action === this.COMMENTACTIONS.REPLY) {
            this.reply = '';
          } else if (action === this.COMMENTACTIONS.EDIT) {
            this.textarea = '';
          }
          this.commentFormTitle = '';
          this.closeAllForms();
        },
      },
      computed: {
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
        this.$root.$on('closeCommentForms', () => {
          this.closeAllForms();
        });
      },
    });

    const app = new Vue({
      el: divElem,
      components: {
        commentUI,
        userAvatarUI,
        faSvg,
        shareDropdown,
      },
      data() {
        return {
          newCommentUrl,
          comments: [],
          isuserloggedin,
          isuserparticipant,
          iscommentmoderator,
          user,
          commentForm: false,
          textarea: '',
          errorMsg: '',
          loginUrl,
          refreshTimer: '',
          headerHeight,
          svgIconUrl: window.Hasgeek.config.svgIconUrl,
          initialLoad: true,
          showmodal: false,
          formTitle: 'New comment',
        };
      },
      methods: {
        showNewCommentForm(event, textareaId) {
          event.preventDefault();
          this.commentForm = true;
          this.formTitle = 'New comment';
          this.showmodal = true;
          this.activateForm(this.COMMENTACTIONS.NEW, textareaId);
        },
        activateForm(action, textareaId, parentApp = app) {
          console.log('textareaId', textareaId);
          if (textareaId) {
            this.$nextTick(() => {
              let editor = window.CodeMirror.fromTextArea(
                document.getElementById(textareaId),
                window.Baseframe.Config.cm_markdown_config
              );
              let delay;
              editor.on('change', function () {
                clearTimeout(delay);
                delay = setTimeout(function () {
                  editor.save();
                  if (action === parentApp.COMMENTACTIONS.REPLY) {
                    parentApp.reply = editor.getValue();
                  } else {
                    console.log('else');
                    parentApp.textarea = editor.getValue();
                  }
                }, 300);
              });
            });
          }
          this.pauseRefreshComments();
        },
        closeModal() {
          this.commentForm = false;
          this.formTitle = '';
          this.showmodal = false;
        },
        submitCommentForm(formId, postUrl, action, parentApp = app) {
          let commentContent = $(`#${formId}`)
            .find('textarea[name="message"]')
            .val();
          console.log('commentContent', commentContent);
          $.ajax({
            url: postUrl,
            type: 'POST',
            data: {
              message: commentContent,
              csrf_token: $('meta[name="csrf-token"]').attr('content'),
            },
            dataType: 'json',
            success(responseData) {
              console.log('responseData', responseData);
              // New comment submit
              if (action === parentApp.COMMENTACTIONS.NEW) {
                parentApp.errorMsg = '';
                parentApp.textarea = '';
                parentApp.closeModal();
              } else {
                parentApp.handleFormSubmit(action);
              }
              if (responseData.comments) {
                app.updateCommentsList(responseData.comments);
                window.toastr.success(responseData.message);
              }
              app.refreshCommentsTimer();
            },
            error(response) {
              console.log('error', response);
              parentApp.errorMsg = Utils.formErrorHandler(formId, response);
            },
          });
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
            window.Hasgeek.config.refreshInterval
          );
        },
        getInitials: window.Baseframe.Utils.getInitials,
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
