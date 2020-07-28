import Vue from 'vue/dist/vue.min';
import VS2 from 'vue-script2';
import * as timeago from 'timeago.js';
import { Utils } from './util';

const Posts = {
  init({
    draft = '',
    posts = '',
    divElem,
    postTemplate,
    isEditor,
    headerHeight,
  }) {
    Vue.use(VS2);

    const postUI = Vue.component('post', {
      template: postTemplate,
      props: ['post', 'iseditor'],
      data() {
        return {
          truncated: true,
          setReadMore: false,
          svgIconUrl: window.HasGeek.config.svgIconUrl,
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
          console.log(
            'age',
            this.post.published_at,
            timeago.format(this.post.published_at)
          );
          return this.now && this.post.published_at
            ? timeago.format(this.post.published_at)
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
        postUI,
      },
      data() {
        return {
          draft: draft.length > 0 ? draft : '',
          posts: posts.length > 0 ? posts : '',
          isEditor,
          headerHeight,
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
      },
    });

    app.$mount(divElem);
  },
};

$(() => {
  window.HasGeek.PostsInit = function (config) {
    Posts.init(config);
  };
});
