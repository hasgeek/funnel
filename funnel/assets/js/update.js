import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import * as timeago from 'timeago.js';
import { Utils } from './util';
import { userAvatarUI, faSvg } from './vue_util';

const Updates = {
  init({
    draft = '',
    updates = '',
    divElem,
    updateTemplate,
    isEditor,
    headerHeight,
    addReadMore,
  }) {
    Vue.use(VS2);

    const updateUI = Vue.component('update', {
      template: updateTemplate,
      props: ['update', 'iseditor', 'addreadmore'],
      data() {
        return {
          truncated: true,
          setReadMore: false,
          svgIconUrl: window.Hasgeek.config.svgIconUrl,
          now: new Date(),
        };
      },
      methods: {
        getInitials: window.Baseframe.Utils.getInitials,
        truncate(content, length) {
          if (!content) return '';
          let value = content.toString();
          if (value.length > length) {
            this.setReadMore = true;
            let txt = `${value.substring(0, length)} ...`;
            return txt;
          } else {
            return value;
          }
        },
        readMore(event, action) {
          event.preventDefault();
          this.setReadMore = action;
          this.truncated = action;
        },
      },
      computed: {
        age() {
          return this.now && this.update.published_at
            ? timeago.format(this.update.published_at)
            : '';
        },
      },
      mounted() {
        window.setInterval(() => {
          this.now = new Date();
        }, 20000);
      },
    });

    const app = new Vue({
      components: {
        updateUI,
        userAvatarUI,
        faSvg,
      },
      data() {
        return {
          draft: draft.length > 0 ? draft : '',
          updates: updates.length > 0 ? updates : '',
          isEditor,
          headerHeight,
          addReadMore,
        };
      },
      mounted() {
        if (window.location.hash) {
          Utils.animateScrollTo(
            document
              .getElementById(window.location.hash)
              .getBoundingClientRect().top - this.headerHeight
          );
        }
        Utils.truncate();
        Utils.addWebShare();
      },
    });

    app.$mount(divElem);
  },
};

$(() => {
  window.Hasgeek.UpdatesInit = function (config) {
    Updates.init(config);
  };
});
