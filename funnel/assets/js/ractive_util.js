import Ractive from 'ractive';

export const useravatar = Ractive.extend({
  template: `{{#if user.profile_url && addprofilelink }}<a href="{{user.profile_url}}">{{#if user.avatar }}<img class="user__box__gravatar" src="{{ user.avatar }}" />{{else}}<div class="user__box__gravatar user__box__gravatar--initials">{{ getInitials(user.fullname) }}</div>{{/if}}</a>{{else}}<span>{{#if user.avatar }}<img class="user__box__gravatar" src="{{ user.avatar }}" />{{else}}<div class="user__box__gravatar user__box__gravatar--initials">{{ getInitials(user.fullname) }}</div>{{/if}}</span>{{/if}}`,
  getInitials: window.Baseframe.Utils.getInitials,
  data: {
    addprofilelink: true,
  },
});

export const faicon = Ractive.extend({
  template:
    '<svg class="fa5-icon {{#if icon_size }}fa5-icon--{{icon_size}}{{/if}} {{#if baseline }}fa5--align-baseline{{/if}} {{#if css_class }}{{css_class}}{{/if}}" aria-hidden="true" role="img"><use xlink:href="{{ svgIconUrl }}#{{icon}}"></use></svg>',
});
