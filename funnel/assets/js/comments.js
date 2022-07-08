import Vue from 'vue/dist/vue.min';
import ScrollHelper from './utils/scrollhelper';
import Form from './utils/formhelper';
import getTimeago from './utils/getTimeago';
import { userAvatarUI, faSvg, shareDropdown } from './utils/vue_util';

const Comments = {
  init({
    newCommentUrl,
    commentsUrl,
    divElem,
    commentTemplate,
    isuserloggedin,
    user,
    loginUrl,
    lastSeenUrl,
  }) {
    const COMMENTACTIONS = {
      REPLY: 0,
      EDIT: 1,
      DELETE: 2,
      REPORTSPAM: 3,
      NEWCOMMENT: 4,
    };

    Vue.mixin({
      created() {
        this.COMMENTACTIONS = COMMENTACTIONS;
      },
    });

    const commentUI = Vue.component('comment', {
      template: commentTemplate,
      props: ['comment', 'user', 'isuserloggedin'],
      data() {
        return {
          errorMsg: '',
          svgIconUrl: window.Hasgeek.Config.svgIconUrl,
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
        getInitials: window.Hasgeek.Utils.getInitials,
        collapse(action) {
          this.hide = action;
        },
        closeAllForms(event) {
          if (event) event.preventDefault();
          if (this.formOpened) {
            this.formOpened = false;
            this.formAction.forEach((commentForm) => {
              this[commentForm.form] = false;
            });
            this.$parent.refreshCommentsTimer();
          }
        },
        refreshCommentsTimer() {
          this.$parent.refreshCommentsTimer();
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
            ? this.timeago.format(
                this.comment.created_at,
                window.Hasgeek.Config.locale
              )
            : '';
        },
        edited_at_age() {
          return this.now && this.comment.edited_at
            ? this.timeago.format(
                this.comment.edited_at,
                window.Hasgeek.Config.locale
              )
            : '';
        },
      },
      created() {
        this.timeago = getTimeago();
      },
      mounted() {
        window.setInterval(() => {
          this.now = new Date();
        }, 20000);
        this.$root.$on('closeCommentForms', () => {
          this.closeAllForms();
        });
        this.$root.$on('clickedOutside', () => {
          if (!this.reply) {
            this.closeAllForms();
          }
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
          user,
          commentForm: false,
          textarea: '',
          errorMsg: '',
          loginUrl,
          lastSeenUrl,
          refreshTimer: '',
          headerHeight: '',
          svgIconUrl: window.Hasgeek.Config.svgIconUrl,
          initialLoad: true,
          showmodal: false,
          formTitle: 'New comment',
          scrollTo: '',
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
          if (textareaId) {
            this.$nextTick(() => {
              const editor = window.CodeMirror.fromTextArea(
                document.getElementById(textareaId),
                window.Hasgeek.Config.cm_markdown_config
              );
              let delay;
              editor.on('change', () => {
                clearTimeout(delay);
                delay = setTimeout(() => {
                  editor.save();
                  if (action === parentApp.COMMENTACTIONS.REPLY) {
                    parentApp.reply = editor.getValue();
                  } else {
                    parentApp.textarea = editor.getValue();
                  }
                }, window.Hasgeek.Config.saveEditorContentTimeout);
              });
              editor.focus();
            });
          }
          this.pauseRefreshComments();
        },
        closeNewCommentForm(event) {
          if (event) event.preventDefault();
          if (this.commentForm) {
            this.commentForm = false;
            this.formTitle = '';
            this.showmodal = false;
            this.refreshCommentsTimer();
          }
        },
        submitCommentForm(formId, postUrl, action, parentApp = app) {
          const commentContent = $(`#${formId}`)
            .find('textarea[name="message"]')
            .val();
          $.ajax({
            url: postUrl,
            type: 'POST',
            data: {
              message: commentContent,
              csrf_token: $('meta[name="csrf-token"]').attr('content'),
            },
            dataType: 'json',
            success(responseData) {
              // New comment submit
              if (action === parentApp.COMMENTACTIONS.NEW) {
                parentApp.errorMsg = '';
                parentApp.textarea = '';
                parentApp.closeNewCommentForm();
              } else {
                parentApp.handleFormSubmit(action);
              }
              if (responseData.comments) {
                app.updateCommentsList(responseData.comments);
                window.toastr.success(responseData.message);
              }
              if (responseData.comment) {
                app.scrollTo = `#c-${responseData.comment.uuid_b58}`;
              }
              app.refreshCommentsTimer();
            },
            error(response) {
              parentApp.errorMsg = Form.formErrorHandler(formId, response);
            },
          });
        },
        updateCommentsList(commentsList) {
          this.comments = commentsList.length > 0 ? commentsList : '';
        },
        fetchCommentsList() {
          $.ajax({
            url: commentsUrl,
            type: 'GET',
            timeout: window.Hasgeek.Config.ajaxTimeout,
            dataType: 'json',
            success(data) {
              app.updateCommentsList(data.comments);
            },
          });
        },
        pauseRefreshComments() {
          clearTimeout(this.refreshTimer);
        },
        refreshCommentsTimer() {
          this.refreshTimer = window.setInterval(
            this.fetchCommentsList,
            window.Hasgeek.Config.refreshInterval
          );
        },
        getInitials: window.Hasgeek.Utils.getInitials,
      },
      mounted() {
        this.fetchCommentsList();
        this.refreshCommentsTimer();
        this.headerHeight = ScrollHelper.getPageHeaderHeight();

        $('body').on('click', (e) => {
          if (
            $('.js-new-comment-form')[0] !== e.target &&
            !$('.js-new-comment-form').find(e.target).length &&
            !$(e.target).parents('.js-comment-form').length
          ) {
            this.$root.$emit('clickedOutside');
          }
        });

        this.$root.$on('clickedOutside', () => {
          if (!this.textarea) {
            this.closeNewCommentForm();
          }
        });

        $(window).resize(() => {
          this.headerHeight = ScrollHelper.getPageHeaderHeight();
        });

        const commentSection = document.querySelector(divElem);
        if (commentSection && lastSeenUrl) {
          const observer = new IntersectionObserver(
            (entries) => {
              entries.forEach((entry) => {
                if (entry.isIntersecting) {
                  $.ajax({
                    url: lastSeenUrl,
                    type: 'POST',
                    data: {
                      csrf_token: $('meta[name="csrf-token"]').attr('content'),
                    },
                    dataType: 'json',
                  });
                  observer.unobserve(commentSection);
                }
              });
            },
            {
              rootMargin: '0px',
              threshold: 0,
            }
          );
          observer.observe(commentSection);
        }
      },
      updated() {
        if (this.initialLoad && window.location.hash) {
          ScrollHelper.animateScrollTo(
            $(window.location.hash).offset().top - this.headerHeight
          );
          this.initialLoad = false;
        }
        if (this.scrollTo) {
          if ($(window).width() < window.Hasgeek.Config.mobileBreakpoint) {
            ScrollHelper.animateScrollTo(
              $(this.scrollTo).offset().top - this.headerHeight
            );
          }
          this.scrollTo = '';
        }
      },
    });
  },
};

$(() => {
  window.Hasgeek.Comments = function initComments(config) {
    $.ajax({
      url: config.codemirrorUrl,
      dataType: 'script',
      cache: true,
    }).done(() => {
      Comments.init(config);
    });
  };
});
