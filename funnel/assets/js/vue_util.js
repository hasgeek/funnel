import Vue from 'vue/dist/vue.min';

export const userAvatarUI = Vue.component('user-avatar', {
  template:
    '<a :href="user.profile_url" v-if="user.profile_url && addprofilelink"><img class="user__box__gravatar" :src="user.avatar" v-if="user.avatar"/><div class="user__box__gravatar user__box__gravatar--initials" v-else>{{ getInitials(user.fullname) }}</div></a v-if="user.profile_url && addprofilelink"></a><span v-else><img class="user__box__gravatar" :src="user.avatar" v-if="user.avatar"/><div class="user__box__gravatar user__box__gravatar--initials" v-else>{{ getInitials(user.fullname) }}</span v-else>',
  props: ['user', 'addprofilelink'],
  methods: {
    getInitials: window.Baseframe.Utils.getInitials,
  },
});

export const faSvg = Vue.component('fa-svg', {
  template:
    '<svg class="fa5-icon" :class="[iconsizecss,baselineclass,cssclass]" aria-hidden="true" role="img"><use v-bind:xlink:href="svgIconUrl + icon"></use></svg>',
  props: {
    icon: String,
    iconsize: {
      type: String,
      default: 'body',
    },
    baseline: {
      type: Boolean,
      default: true,
    },
    cssclass: String,
  },
  data() {
    return {
      svgIconUrl: window.Hasgeek.config.svgIconUrl + '#',
    };
  },
  computed: {
    iconsizecss() {
      return 'fa5-icon--' + this.iconsize;
    },
    baselineclass() {
      if (this.baseline) {
        return 'fa5--align-baseline';
      } else return '';
    },
  },
});
