import Ractive from 'ractive';
import Utils from './helper';
import { USER_AVATAR_IMG_SIZE } from '../constants';

Ractive.DEBUG = false;

export const useravatar = Ractive.extend({
  template: `{{#if user.profile_url && addprofilelink }}<a href="{{user.profile_url}}" class="nounderline">{{#if user.logo_url }}<img class="user__box__gravatar" src="{{ imgurl() }}" />{{else}}<div class="user__box__gravatar user__box__gravatar--initials" data-avatar-colour="{{ getAvatarColour(user.fullname) }}">{{ getInitials(user.fullname) }}</div>{{/if}}</a>{{else}}<span>{{#if user.logo_url }}<img class="user__box__gravatar" src="{{ imgurl() }}" />{{else}}<div class="user__box__gravatar user__box__gravatar--initials"  data-avatar-colour="{{ getAvatarColour(user.fullname) }}">{{ getInitials(user.fullname) }}</div>{{/if}}</span>{{/if}}`,
  data: {
    addprofilelink: true,
    size: 'medium',
    getInitials: Utils.getInitials,
    imgurl() {
      return `${this.get('user').logo_url}?size=${encodeURIComponent(
        USER_AVATAR_IMG_SIZE[this.get('size')]
      )}`;
    },
    getAvatarColour(name) {
      return Utils.getAvatarColour(name);
    },
  },
});

export const faicon = Ractive.extend({
  template:
    '<svg class="fa5-icon {{#if icon_size }}fa5-icon--{{icon_size}}{{/if}} {{#if baseline }}fa5--align-baseline{{/if}} {{#if css_class }}{{css_class}}{{/if}}" aria-hidden="true" role="img"><use xlink:href="{{ svgIconUrl }}#{{icon}}"></use></svg>',
  data: {
    svgIconUrl: window.Hasgeek.Config.svgIconUrl,
  },
});

export const RactiveApp = Ractive.extend({
  data: {
    gettext(msgid, ...args) {
      return window.gettext(msgid, ...args);
    },
    ngettext(msgid, msgidPlural, num, ...args) {
      return window.ngettext(msgid, msgidPlural, num, ...args);
    },
  },
  components: { useravatar, faicon },
});
