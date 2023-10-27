import Vue from 'vue/dist/vue.min';
import Utils from './helper';
import WebShare from './webshare';
import { USER_AVATAR_IMG_SIZE } from '../constants';

export const userAvatarUI = Vue.component('useravatar', {
  template:
    '<a :href="user.absolute_url" v-if="addprofilelink" class="nounderline"><span class="user__box__wrapper" v-if="user.logo_url"><img class="user__box__gravatar" :src="imgurl"></span><div class="user__box__gravatar user__box__gravatar--initials" :data-avatar-colour="getAvatarColour(user.fullname)" v-else>{{ getInitials(user.fullname) }}</div></a v-if="user.absolute_url && addprofilelink"></a><span v-else><img class="user__box__gravatar" :src="imgurl" v-if="user.logo_url"/><div class="user__box__gravatar user__box__gravatar--initials" :data-avatar-colour="getAvatarColour(user.fullname)" v-else>{{ getInitials(user.fullname) }}</span v-else>',
  props: {
    user: Object,
    addprofilelink: {
      type: Boolean,
      default: true,
    },
    size: {
      type: String,
      default: 'medium',
    },
  },
  methods: {
    getInitials: Utils.getInitials,
    getAvatarColour: Utils.getAvatarColour,
  },
  computed: {
    imgsize() {
      return USER_AVATAR_IMG_SIZE[this.size];
    },
    imgurl() {
      return `${this.user.logo_url}?size=${encodeURIComponent(this.imgsize)}`;
    },
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
      svgIconUrl: window.Hasgeek.Config.svgIconUrl,
    };
  },
  computed: {
    iconname() {
      return `#${this.icon}`;
    },
    iconsizecss() {
      return `fa5-icon--${this.icon_size}`;
    },
    baselineclass() {
      if (this.baseline) {
        return 'fa5--align-baseline';
      }
      return '';
    },
  },
});

export const shareDropdown = Vue.component('sharedropdown', {
  template: `<ul class="mui-dropdown__menu mui-dropdown__menu--hg-link" data-cy="share-dropdown"><li><a class="mui--text-body2 js-copy-link" href="javascript:void(0)" data-ga="Copy link"><faicon :icon="'copy'" :baseline=true :css_class="'mui--text-light fa-icon--right-margin'"></faicon>{{ window.gettext('Copy link') }}<span class="js-copy-url" aria-hidden="true">{{ url }}</span></a></li><li><a class="mui--text-body2" :href="emailUrl" data-ga="Share via Email"><faicon :icon="'envelope'" :baseline=true :css_class="'mui--text-light fa-icon--right-margin'"></faicon>{{ window.gettext('Email') }}</a></li><li><a class="mui--text-body2" target="_blank" rel="noopener" :href="twitterUrl" :data-url="url" data-via="Hasgeek" :data-text="title" data-ga="Tweet"><faicon :icon="'twitter-square'" :baseline=true :css_class="'mui--text-light fa-icon--right-margin'"></faicon>{{ window.gettext('Twitter') }}</a></li><li><a class="mui--text-body2" target="_blank" rel="noopener" :href="facebookUrl" :data-href="url" data-ga="Share on facebook"><faicon :icon="'facebook-square'" :baseline=true :css_class="'mui--text-light fa-icon--right-margin'"></faicon>{{ window.gettext('Facebook') }}</a></li><li><a class="mui--text-body2" :href="linkedinUrl" data-ga="Share about on linkedin"><faicon :icon="'linkedin'" :baseline=true :css_class="'mui--text-light fa-icon--right-margin'"></faicon>{{ window.gettext('Linkedin') }}</a></li><ul>`,
  props: ['url', 'title'],
  components: {
    faSvg,
  },
  computed: {
    twitterUrl() {
      return `https://twitter.com/share?url=${encodeURIComponent(
        this.url
      )}&amp;text=${encodeURIComponent(this.title)}+(via+@hasgeek)`;
    },
    facebookUrl() {
      return `https://www.facebook.com/sharer.php?u=${encodeURIComponent(
        this.url
      )}&amp;t=${encodeURIComponent(this.title)}`;
    },
    emailUrl() {
      return `mailto:?subject=${encodeURIComponent(
        this.title
      )}&amp;body=${encodeURIComponent(this.url)}`;
    },
    linkedinUrl() {
      return `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(
        this.url
      )}&title=${encodeURIComponent(this.title)}`;
    },
  },
  mounted() {
    WebShare.enableWebShare();
  },
});
