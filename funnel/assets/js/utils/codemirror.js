import { EditorView, keymap } from '@codemirror/view';
import { markdown, markdownLanguage, markdownKeymap } from '@codemirror/lang-markdown';
import { html } from '@codemirror/lang-html';
import { closeBrackets } from '@codemirror/autocomplete';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import {
  syntaxHighlighting,
  defaultHighlightStyle,
  HighlightStyle,
  foldGutter,
} from '@codemirror/language';
import { tags } from '@lezer/highlight';

function codemirrorHelper(markdownId, updateFnCallback = '', callbackInterval = 1000) {
  let textareaWaitTimer;

  const markdownHighlighting = HighlightStyle.define([
    { tag: tags.heading1, fontWeight: 'bold', class: 'cm-heading1' },
    { tag: tags.heading2, fontWeight: 'bold', class: 'cm-heading2' },
    { tag: tags.heading3, fontWeight: 'bold', class: 'cm-heading3' },
    { tag: tags.heading4, fontWeight: 'bold', class: 'cm-heading4' },
    { tag: tags.heading5, fontWeight: 'bold', class: 'cm-heading5' },
    { tag: tags.list, class: 'cm-list' },
    { tag: tags.link, class: 'cm-link' },
    { tag: tags.monospace, class: 'cm-code' },
    { tag: tags.emphasis, fontWeight: 'bold', class: 'cm-emphasis' },
    { tag: tags.strong, fontWeight: 'bold', class: 'cm-strong' },
    { tag: tags.strikethrough, class: 'cm-strikethrough' },
  ]);

  const extensions = [
    EditorView.lineWrapping,
    closeBrackets(),
    history(),
    foldGutter(),
    syntaxHighlighting(markdownHighlighting),
    syntaxHighlighting(defaultHighlightStyle),
    keymap.of([defaultKeymap, markdownKeymap, historyKeymap]),
    markdown({ base: markdownLanguage }),
    html(),
  ];

  const view = new EditorView({
    doc: $(`#${markdownId}`).val(),
    extensions,
    dispatch: (tr) => {
      view.update([tr]);
      $(`#${markdownId}`).val(view.state.doc.toString());
      if (updateFnCallback) {
        if (textareaWaitTimer) clearTimeout(textareaWaitTimer);
        textareaWaitTimer = setTimeout(() => {
          updateFnCallback(view);
        }, callbackInterval);
      }
    },
  });
  document.querySelector(`#${markdownId}`).parentNode.append(view.dom);
  return view;
}

export default codemirrorHelper;
