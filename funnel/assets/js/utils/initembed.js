import addVegaSupport from './vegaembed';
import TypeformEmbed from './typeform_embed';
import MarkmapEmbed from './markmap';
import MermaidEmbed from './mermaid';
import PrismEmbed from './prism';

export default function initEmbed(parentContainer = '') {
  addVegaSupport();
  if (parentContainer) TypeformEmbed.init(parentContainer);
  MarkmapEmbed.init(parentContainer);
  MermaidEmbed.init(parentContainer);
  PrismEmbed.init(parentContainer);
}
