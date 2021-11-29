import Vue from 'vue/dist/vue.min';
import Utils from './helper';

export const userAvatarUI = Vue.component('useravatar', {
  template:
    '<a :href="user.profile_url" v-if="user.profile_url && addprofilelink" class="nounderline"><span class="user__box__wrapper" v-if="user.avatar"><img class="user__box__gravatar" :src="imgurl"></span><div class="user__box__gravatar user__box__gravatar--initials" v-else>{{ getInitials(user.fullname) }}</div></a v-if="user.profile_url && addprofilelink"></a><span v-else><img class="user__box__gravatar" :src="imgurl" v-if="user.avatar"/><div class="user__box__gravatar user__box__gravatar--initials" v-else>{{ getInitials(user.fullname) }}</span v-else>',
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
    getInitials: window.Hasgeek.Utils.getInitials,
  },
  computed: {
    imgsize() {
      return window.Hasgeek.Config.userAvatarImgSize[this.size];
    },
    imgurl() {
      return `${this.user.avatar}?size=${this.imgsize}`;
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
      return `//twitter.com/share?url=${this.url}&amp;via=Hasgeek&amp;text=${this.title}&amp;utm_campaign=share-twitter`;
    },
    facebookUrl() {
      return `//www.facebook.com/sharer.php?u=${this.url}&amp;t=${this.title}&amp;utm_campaign=share-facebook`;
    },
    emailUrl() {
      return `mailto:?subject=${this.title}&amp;body=${this.url}&amp;utm_campaign=share-email`;
    },
    linkedinUrl() {
      return `https://www.linkedin.com/shareArticle?mini=true&url=${this.url}&title=${this.title}&amp;utm_campaign=share-linkedin`;
    },
  },
  mounted() {
    Utils.enableWebShare();
  },
});
