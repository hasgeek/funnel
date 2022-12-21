import addVegaSupport from './vegaembed';
import TypeformEmbed from './typeform_embed';
import MarkmapEmbed from './markmap';
import addMermaidEmbed from './mermaid';
import PrismEmbed from './prism';

export default function initEmbed(parentContainer = '') {
  if (parentContainer) TypeformEmbed.init(parentContainer);
  addVegaSupport(parentContainer);
  MarkmapEmbed.init(parentContainer);
  addMermaidEmbed(parentContainer);
  PrismEmbed.init(parentContainer);
}
