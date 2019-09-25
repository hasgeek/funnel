import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import { Utils, SaveProject } from './util';

const Membership = {
  init({
    newMemberUrl,
    members = '',
    divElem,
    memberTemplate,
    isUserProfileAdmin,
  }) {
    Vue.use(VS2);

    const memberUI = Vue.component('member', {
      template: memberTemplate,
      props: ['member'],
      methods: {
        rolesCount(member) {
          let count = 0;
          if (member.is_editor) count += 1;
          if (member.is_concierge) count += 1;
          if (member.is_usher) count += 1;
          return count - 1;
        },
      },
    });

    /* eslint-disable no-new */
    new Vue({
      el: divElem,
      components: {
        memberUI,
      },
      data() {
        return {
          newMemberUrl,
          members: members.length > 0 ? members : '',
          isUserProfileAdmin,
          roles: [
            {
              roleKey: 'is_editor',
              roleName: 'Editor',
              showMembers: false,
            },
            {
              roleKey: 'is_concierge',
              roleName: 'Concierge',
              showMembers: false,
            },
            {
              roleKey: 'is_usher',
              roleName: 'Usher',
              showMembers: false,
            },
          ],
          memberForm: '',
          activeMember: '',
          errorMsg: '',
          view: 'name',
          search: '',
          showInfo: false,
        };
      },
      methods: {
        fetchForm(event, url, member = '') {
          event.preventDefault();
          if (this.isUserProfileAdmin) {
            this.activeMember = member;
            const app = this;
            $.ajax({
              type: 'GET',
              url,
              timeout: window.HasGeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                const vueFormHtml = data.form;
                app.memberForm = vueFormHtml.replace(/\bscript\b/g, 'script2');
                $('#member-form').modal('show');
              },
            });
          }
        },
        activateForm() {
          const formId = Utils.getElementId(this.memberForm);
          const url = Utils.getActionUrl(formId);
          const app = this;
          const onSuccess = (responseData) => {
            this.closeForm();
            if (responseData.memberships) {
              app.updateMembersList(responseData.memberships);
            }
          };
          const onError = (response) => {
            this.errorMsg = Utils.formErrorHandler(formId, response);
          };
          window.Baseframe.Forms.handleFormSubmit(
            formId,
            url,
            onSuccess,
            onError,
            {
            },
          );
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
            members.filter((member) => {
              member.hide =
                member.user_details.fullname
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
          return this.activeMember.delete_url;
        },
      },
      mounted() {
        $('#member-form').on($.modal.CLOSE, () => {
          this.closeForm();
        });
      },
    });
  },
};

$(() => {
  window.HasGeek.Membership = function (config, saveProjectConfig = '') {
    Membership.init(config);

    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }
  };
});
