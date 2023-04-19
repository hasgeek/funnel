import { Widgets } from './utils/formWidgets';

$(() => {
  window.Hasgeek.cfpInit = function submissionsInit({ openSubmission = '' }) {
    Widgets.openSubmissionToggle(openSubmission.toggleId, openSubmission.cfpStatusElem);
  };
});
