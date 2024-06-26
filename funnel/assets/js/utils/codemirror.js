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
import { languages } from '@codemirror/language-data';
import { mermaidLanguageDescription } from 'codemirror-lang-mermaid';

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
    { tag: tags.emphasis, class: 'cm-emphasis' },
    { tag: tags.strong, fontWeight: 'bold', class: 'cm-strong' },
    { tag: tags.strikethrough, class: 'cm-strikethrough' },
  ]);

  const extensions = [
    EditorView.lineWrapping,
    EditorView.contentAttributes.of({ autocapitalize: 'on' }),
    closeBrackets(),
    history(),
    foldGutter(),
    syntaxHighlighting(markdownHighlighting),
    syntaxHighlighting(defaultHighlightStyle),
    keymap.of([defaultKeymap, markdownKeymap, historyKeymap]),
    markdown({
      base: markdownLanguage,
      codeLanguages: [...languages, mermaidLanguageDescription],
    }),
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

  $(`#${markdownId}`).addClass('activated').removeClass('activating');
  document.querySelector(`#${markdownId}`).parentNode.append(view.dom);
  return view;
}

export default codemirrorHelper;
