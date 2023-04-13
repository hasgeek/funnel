import { EditorView, keymap } from '@codemirror/view';
import { css, cssLanguage } from '@codemirror/lang-css';
import { closeBrackets } from '@codemirror/autocomplete';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import {
  syntaxHighlighting,
  defaultHighlightStyle,
  foldGutter,
} from '@codemirror/language';

function codemirrorStylesheetHelper(
  textareaId,
  updateFnCallback = '',
  callbackInterval = 1000
) {
  let textareaWaitTimer;

  const extensions = [
    EditorView.lineWrapping,
    EditorView.contentAttributes.of({ autocapitalize: 'on' }),
    closeBrackets(),
    history(),
    foldGutter(),
    syntaxHighlighting(defaultHighlightStyle),
    keymap.of([defaultKeymap, historyKeymap]),
    css({ base: cssLanguage }),
  ];

  const view = new EditorView({
    doc: $(`#${textareaId}`).val(),
    extensions,
    dispatch: (tr) => {
      view.update([tr]);
      $(`#${textareaId}`).val(view.state.doc.toString());
      if (updateFnCallback) {
        if (textareaWaitTimer) clearTimeout(textareaWaitTimer);
        textareaWaitTimer = setTimeout(() => {
          updateFnCallback(view);
        }, callbackInterval);
      }
    },
  });
  document.querySelector(`#${textareaId}`).parentNode.append(view.dom);
  return view;
}

export default codemirrorStylesheetHelper;
