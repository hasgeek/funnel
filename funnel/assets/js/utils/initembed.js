import addVegaSupport from './vegaembed';
import TypeformEmbed from './typeform_embed';
import MarkmapEmbed from './markmap';
import MermaidEmbed from './mermaid';
import PrismEmbed from './prism';

export default function initEmbed(markdownElem = '') {
  addVegaSupport();
  if (markdownElem) TypeformEmbed.init(markdownElem);
  MarkmapEmbed.init();
  MermaidEmbed.init();
  PrismEmbed.init(markdownElem);
}
