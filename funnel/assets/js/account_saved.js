import { SaveProject } from './util';

$(() => {
  $('.js-save-form').each(function () {
    let projectSaveConfig = {
      formId: $(this).attr('id'),
      postUrl: $(this).attr('action'),
    };
    SaveProject(projectSaveConfig);
  });
});
