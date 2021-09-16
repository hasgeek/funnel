import * as timeago from 'timeago.js';
/* eslint camelcase: ["error", {allow: ["hi_IN"]}] */
import hi_IN from 'timeago.js/lib/lang/hi_IN';

function getTimeago() {
  // en_US and zh_CN are built in timeago, other languages required to be registered.
  timeago.register('hi_IN', hi_IN);
  return timeago;
}

export default getTimeago;
