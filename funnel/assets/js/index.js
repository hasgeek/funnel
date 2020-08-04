import { SaveProject } from './util';
import Vue from 'vue/dist/vue.min';

$(() => {
  window.Hasgeek.HomeInit = function (config) {
    // Expand CFP section
    $('.jquery-show-all').click(function showAll(event) {
      event.preventDefault();
      const projectElemClass = `.${$(this).data('projects')}`;
      $(projectElemClass).removeClass('mui--hide');
      $(this).addClass('mui--hide');
    });

    $('.js-save-form').each(function () {
      let projectSaveConfig = {
        formId: $(this).attr('id'),
        postUrl: $(this).attr('action'),
      };
      SaveProject(projectSaveConfig);
    });

    const pastProjectsApp = new Vue({
      el: '#past-project-table',
      data() {
        return {
          title: '',
          headings: [],
          pastprojects: [],
          next_page: 1,
          waitingForResponse: false,
        };
      },
      methods: {
        fetchResult() {
          if (!pastProjectsApp.waitingForResponse) {
            pastProjectsApp.waitingForResponse = true;
            $.ajax({
              type: 'GET',
              url: config.past_projects_json_url,
              data: {
                page: pastProjectsApp.next_page,
              },
              timeout: window.Hasgeek.config.ajaxTimeout,
              dataType: 'json',
              success(data) {
                pastProjectsApp.title = data.title;
                pastProjectsApp.headings = data.headings;
                pastProjectsApp.pastprojects.push(...data.past_projects);
                pastProjectsApp.next_page = data.next_page;
                pastProjectsApp.waitingForResponse = false;
              },
            });
          }
        },
        lazyoad() {
          const lazyLoader = document.querySelector('.js-lazy-loader');
          if (lazyLoader) {
            this.handleObserver = this.handleObserver.bind(this);

            const observer = new IntersectionObserver(this.handleObserver, {
              rootMargin: '0px',
              threshold: 0,
            });
            observer.observe(lazyLoader);
          }
        },
        handleObserver(entries) {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.fetchResult();
            }
          });
        },
      },
      mounted() {
        this.lazyoad();
      },
    });
  };
});
