import SaveProject from './utils/bookmark';

$(() => {
  $('.js-save-form').each(function saveProjectButton() {
    const projectSaveConfig = {
      formId: $(this).attr('id'),
      postUrl: $(this).attr('action'),
    };
    SaveProject(projectSaveConfig);
  });
});
