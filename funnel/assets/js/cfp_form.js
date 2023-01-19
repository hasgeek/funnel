import Form from './utils/formhelper';

$(() => {
  window.Hasgeek.cfpInit = function submissionsInit({ openSubmission = '' }) {
    Form.openSubmissionToggle(openSubmission.toggleId, openSubmission.cfpStatusElem);
  };
});
