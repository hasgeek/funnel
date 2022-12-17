import addVegaSupport from './vegaembed';
import TypeformEmbed from './typeform_embed';
import MarkmapEmbed from './markmap';
import MermaidEmbed from './mermaid';
import PrismEmbed from './prism';

export default function initEmbed(parentContainer = '') {
  if (parentContainer) {
    TypeformEmbed.init(parentContainer);
    addVegaSupport(parentContainer);
    MarkmapEmbed.init(parentContainer);
    MermaidEmbed.init(parentContainer);
    PrismEmbed.init(parentContainer);
  }
}
