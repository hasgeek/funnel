import addVegaSupport from './vegaembed';
import TypeformEmbed from './typeform_embed';
import MarkmapEmbed from './markmap';
import MermaidEmbed from './mermaid';

export default function initEmbed(markdownElem = '') {
  addVegaSupport();
  if (markdownElem) TypeformEmbed.init(markdownElem);
  MarkmapEmbed.init();
  MermaidEmbed.init();
}
