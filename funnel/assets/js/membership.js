import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import toastr from 'toastr';
import { MOBILE_BREAKPOINT } from './constants';
import Form from './utils/formhelper';
import Utils from './utils/helper';
import { userAvatarUI, faSvg } from './utils/vue_util';

const Membership = {
  init({
    newMemberUrl,
    members = '',
    roles = [],
    divElem,
    memberTemplate,
    isUserProfileAdmin,
  }) {
    Vue.use(VS2);

    const memberUI = Vue.component('membership', {
      template: memberTemplate,
      props: ['membership'],
      methods: {
        rolesCount(membership) {
          let count = 0;
          if (membership.is_editor) count += 1;
          if (membership.is_promoter) count += 1;
          if (membership.is_usher) count += 1;
          return count - 1;
        },
        getInitials: Utils.getInitials,
        getAvatarColour: Utils.getAvatarColour,
      },
    });

    /* eslint-disable no-new */
    new Vue({
      el: divElem,
      components: {
        memberUI,
        userAvatarUI,
        faSvg,
      },
      data() {
        return {
          newMemberUrl,
          members: members.length > 0 ? members : '',
          isUserProfileAdmin,
          roles,
          memberForm: '',
          activeMember: '',
          errorMsg: '',
          view: 'name',
          search: '',
          showInfo: false,
          svgIconUrl: window.Hasgeek.Config.svgIconUrl,
          isMobile: false,
          ready: false,
        };
      },
      methods: {
        async fetchForm(event, url, member = '') {
          event.preventDefault();
          if (this.isUserProfileAdmin) {
            this.activeMember = member;
            const app = this;
            const response = await fetch(url, {
              headers: {
                Accept: 'application/json',
              },
            }).catch(() => {
              toastr.error(window.Hasgeek.Config.errorMsg.networkError);
            });
            if (response && response.ok) {
              const data = await response.json();
              if (data) {
                const vueFormHtml = data.form;
                app.memberForm = vueFormHtml.replace(/\bscript\b/g, 'script2');
                app.errorMsg = '';
                $('#member-form').modal('show');
              }
            } else {
              Form.getResponseError(response);
            }
          }
        },
        activateForm() {
          const formId = Form.getElementId(this.memberForm);
          const url = Form.getActionUrl(formId);
          const onSuccess = (responseData) => {
            this.closeForm();
            if (responseData.memberships) {
              this.updateMembersList(responseData.memberships);
              this.onChange();
              toastr.success(responseData.message);
            }
          };
          const onError = (response) => {
            this.errorMsg = Form.formErrorHandler(formId, response);
          };
          Form.handleFormSubmit(formId, url, onSuccess, onError, {});
        },
        updateMembersList(membersList) {
          this.members = membersList.length > 0 ? membersList : '';
        },
        filter(event, action) {
          event.preventDefault();
          this.view = action;
        },
        closeForm(event = '') {
          if (event) event.preventDefault();
          $.modal.close();
          this.errorMsg = '';
        },
        onChange() {
          if (this.search) {
            this.members.filter((member) => {
              member.hide =
                member.user.fullname
                  .toLowerCase()
                  .indexOf(this.search.toLowerCase()) === -1;
              return true;
            });
          }
        },
        collapse(event, role) {
          event.preventDefault();
          role.showMembers = !role.showMembers;
        },
        showRoleDetails(event) {
          event.preventDefault();
          this.showInfo = !this.showInfo;
        },
        onWindowResize() {
          this.isMobile = $(window).width() < MOBILE_BREAKPOINT;
        },
      },
      computed: {
        Form() {
          const template = this.memberForm ? this.memberForm : '<div></div>';
          const isFormTemplate = this.memberForm ? true : '';
          return {
            template,
            mounted() {
              if (isFormTemplate) {
                this.$parent.activateForm();
              }
            },
          };
        },
        deleteURL() {
          return this.activeMember.urls.delete;
        },
      },
      mounted() {
        $('#member-form').on($.modal.CLOSE, () => {
          this.closeForm();
        });
        this.ready = true;
      },
      created() {
        window.addEventListener('resize', this.onWindowResize);
      },
    });
  },
};

$(() => {
  window.Hasgeek.membershipInit = (config) => {
    Membership.init(config);
  };
});
