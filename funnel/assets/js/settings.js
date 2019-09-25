import { SaveProject } from './util';

$(() => {
  window.HasGeek.Settings = function init(saveProjectConfig = '') {
    if (saveProjectConfig) {
      SaveProject(saveProjectConfig);
    }
  };
});
