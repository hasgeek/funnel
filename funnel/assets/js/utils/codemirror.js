import { EditorView, placeholder, keymap } from '@codemirror/view';
import { markdown, markdownLanguage, markdownKeymap } from '@codemirror/lang-markdown';
import { html } from '@codemirror/lang-html';
import { closeBrackets } from '@codemirror/autocomplete';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { syntaxHighlighting, HighlightStyle } from '@codemirror/language';
import { tags } from '@lezer/highlight';

function codemirrorHelper(markdownId, updateFnCallback = '', callbackInterval = 1000) {
  let textareaWaitTimer;

  const markdownHighlighting = HighlightStyle.define([
    { tag: tags.heading1, fontWeight: 'bold' },
    { tag: tags.heading2, fontWeight: 'bold' },
    { tag: tags.heading3, fontWeight: 'bold' },
    { tag: tags.heading4, fontWeight: 'bold' },
    { tag: tags.heading5, fontWeight: 'bold' },
    { tag: tags.list },
    { tag: tags.link },
    { tag: tags.quote },
    { tag: tags.comment },
    { tag: tags.emphasis },
    { tag: tags.strong },
    { tag: tags.monospace },
    { tag: tags.strikethrough },
  ]);

  const extensions = [
    EditorView.lineWrapping,
    placeholder('Content'),
    closeBrackets(),
    history(),
    syntaxHighlighting(markdownHighlighting),
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
}

export default codemirrorHelper;
