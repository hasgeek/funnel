import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import Utils from './utils/helper';
import ScrollHelper from './utils/scrollhelper';
import getTimeago from './utils/getTimeago';
import { userAvatarUI, faSvg, shareDropdown } from './utils/vue_util';

const Updates = {
  init({ draft = '', updates = '', divElem, updateTemplate, isEditor, addReadMore }) {
    Vue.use(VS2);

    const updateUI = Vue.component('update', {
      template: updateTemplate,
      props: ['update', 'iseditor', 'addreadmore'],
      data() {
        return {
          truncated: true,
          setReadMore: false,
          svgIconUrl: window.Hasgeek.Config.svgIconUrl,
          now: new Date(),
        };
      },
      methods: {
        getInitials: Utils.getInitials,
        truncate(content, length) {
          if (!content) return '';
          const value = content.toString();
          if (value.length > length) {
            this.setReadMore = true;
            const txt = `${value.substring(0, length)} ...`;
            return txt;
          }
          return value;
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
            ? this.timeago.format(
                this.update.published_at,
                window.Hasgeek.Config.locale
              )
            : '';
        },
      },
      created() {
        this.timeago = getTimeago();
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
        shareDropdown,
      },
      data() {
        return {
          draft: draft.length > 0 ? draft : '',
          updates: updates.length > 0 ? updates : '',
          isEditor,
          headerHeight: '',
          addReadMore,
        };
      },
      mounted() {
        this.headerHeight = ScrollHelper.getPageHeaderHeight();
        if (window.location.hash) {
          ScrollHelper.animateScrollTo(
            document.getElementById(window.location.hash).getBoundingClientRect().top -
              this.headerHeight
          );
        }
        Utils.truncate();

        $(window).resize(() => {
          this.headerHeight = ScrollHelper.getPageHeaderHeight();
        });
      },
    });

    app.$mount(divElem);
  },
};

$(() => {
  window.Hasgeek.updatesInit = function updatesInit(config) {
    Updates.init(config);
  };
});
