import { Widgets } from './utils/formwidgets';

$(() => {
  window.Hasgeek.cfpInit = function submissionsInit({ openSubmission = '' }) {
    Widgets.openSubmissionToggle(openSubmission.toggleId, openSubmission.cfpStatusElem);
  };
});
