import Vue from 'vue/dist/vue.min';

export const userAvatarUI = Vue.component('useravatar', {
  template:
    '<a :href="user.profile_url" v-if="user.profile_url && addprofilelink"><img class="user__box__gravatar" :src="user.avatar" v-if="user.avatar"/><div class="user__box__gravatar user__box__gravatar--initials" v-else>{{ getInitials(user.fullname) }}</div></a v-if="user.profile_url && addprofilelink"></a><span v-else><img class="user__box__gravatar" :src="user.avatar" v-if="user.avatar"/><div class="user__box__gravatar user__box__gravatar--initials" v-else>{{ getInitials(user.fullname) }}</span v-else>',
  props: ['user', 'addprofilelink'],
  methods: {
    getInitials: window.Baseframe.Utils.getInitials,
  },
});

export const faSvg = Vue.component('faicon', {
  template:
    '<svg class="fa5-icon" :class="[iconsizecss,baselineclass,css_class]" aria-hidden="true" role="img"><use v-bind:xlink:href="svgIconUrl + iconname"></use></svg>',
  props: {
    icon: String,
    icon_size: {
      type: String,
      default: 'body',
    },
    baseline: {
      type: Boolean,
      default: true,
    },
    css_class: String,
  },
  data() {
    return {
      svgIconUrl: window.Hasgeek.config.svgIconUrl,
    };
  },
  computed: {
    iconname() {
      return '#' + this.icon;
    },
    iconsizecss() {
      return 'fa5-icon--' + this.icon_size;
    },
    baselineclass() {
      if (this.baseline) {
        return 'fa5--align-baseline';
      } else return '';
    },
  },
});
