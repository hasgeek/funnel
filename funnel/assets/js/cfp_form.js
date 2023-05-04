import { Widgets } from './utils/form_widgets';

$(() => {
  window.Hasgeek.cfpInit = function submissionsInit({ openSubmission = '' }) {
    Widgets.openSubmissionToggle(openSubmission.toggleId, openSubmission.cfpStatusElem);
  };
});
