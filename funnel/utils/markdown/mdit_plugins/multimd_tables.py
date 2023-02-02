from copy import copy
import re

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.token import Token

from .mmd_dfa import DFA

from functools import partial

BACKSLASH_CHAR = 0x5c  # ASCII value for `\`
BACKTICK_CHAR = 0x60  # ASCII value for `\``
PIPE_CHAR = 0x7c  # ASCII value for `|`

CAPTION_RE = re.compile(r'^\[(.+?)\](\[([^\[\]]+)\])?\s*$')
SEPERATOR_RE = re.compile(r'^:?(-+|=+):?\+?$')

def multimd_table_plugin(md: MarkdownIt, **options):
    defaults = {
        "multiline":  False,
        "rowspan":    False,
        "headerless": False,
        "multibody":  True,
        "autolabel":  True
    }
    options = {**defaults, **options} if options else defaults

    def scan_bound_indices(state: StateBlock, line):
        """
        Naming convention of positional variables
        - list-item
        ·········longtext······\n
        ^head  ^start  ^end  ^max
        """
        start = state.bMarks[line] + state.sCount[line]
        head = state.bMarks[line] + state.blkIndent
        end = state.skipSpacesBack(state.eMarks[line], head)
        bounds = []
        pos = start
        posjump = 0
        escape = False
        code = False

        # Scan for valid pipe character position
        while pos < end:
            if state.srcCharCode[pos] == BACKSLASH_CHAR:
                escape = True
            elif state.srcCharCode[pos] == BACKTICK_CHAR:
                posjump = state.skipChars(pos, BACKTICK_CHAR)
                if posjump > pos:
                    pos = posjump
                elif code or not escape:
                    code = not code
                escape = False
            elif state.srcCharCode[pos] == PIPE_CHAR:
                if not code and not escape:
                    bounds.append(pos)
                escape = False
            else:
                escape = False

            pos += 1

        if len(bounds) == 0:
            return bounds

        # Pad in newline characters on last and this line
        if bounds[0] > head:
            bounds.insert(0, head - 1)
        if bounds[-1] < end - 1:
            bounds.append(end)

        return bounds
    
    def table_caption(state: StateBlock, silent, line):
        meta = {'text': None, 'label': None}
        start = state.bMarks[line] + state.sCount[line]
        max_ = state.eMarks[line]
        matches = CAPTION_RE.match(state.src[start:max_])

        if not matches:
            return False
        if silent:
            return True

        meta['text'] = matches.group(1)

        if not options['autolabel'] and not matches.group(2):
            return meta

        meta['label'] = matches.group(2) or matches.group(1)
        meta['label'] = meta['label'].lower().replace('\W+', '')

        return meta

    def table_row(state: StateBlock, silent, line):
        meta = { 'bounds': None, 'multiline': None }
        bounds = scan_bound_indices(state, line)
        start, pos, old_max = None, None, None

        if len(bounds) < 2:
            return False
        if silent:
            return True

        meta['bounds'] = bounds

        if options['multiline']:
            start = state.bMarks[line] + state.sCount[line]
            pos = state.eMarks[line] - 1  # where backslash should be 
            meta['multiline'] = state.srcCharCode[pos] == BACKSLASH_CHAR # \
            if meta['multiline']:
                old_max = state.eMarks[line]
                state.eMarks[line] = state.skipSpacesBack(pos, start)
                meta['bounds'] = scan_bound_indices(state, line)
                state.eMarks[line] = old_max

        return meta

    def table_separator(state: StateBlock, silent, line):
        meta = {'aligns': [], 'wraps': []}
        bounds = scan_bound_indices(state, line)
        c = 0
        text = ''
        align = 0

        # Only separator needs to check indents
        if state.sCount[line] - state.blkIndent >= 4:
            return False
        if len(bounds) == 0:
            return False

        for c in range(len(bounds) - 1):
            text = state.src[bounds[c] + 1: bounds[c + 1]].strip()
            if not SEPERATOR_RE.match(text):
                return False

            meta['wraps'].append(text[-1] == '+')
            align = ((text[0] == ':') << 4) | (text[-1 - meta['wraps'][c]] == ':')
            if align == 0x00:
                meta['aligns'].append('')
            elif align == 0x01:
                meta['aligns'].append('right')
            elif align == 0x10:
                meta['aligns'].append('left')
            elif align == 0x11:
                meta['aligns'].append('center')

        if silent:
            return True
        return meta

    def table_empty(state: StateBlock, silent, line):
        return state.isEmpty(line)

    def table(state: StateBlock, start_line, end_line, silent):
        table_dfa = DFA()
        # These are already initialised in the object
        # table_dfa.grp = 0x10
        # table_dfa.mtr = -1
        # table_dfa.tgroup_lines = None
        # table_dfa.colspan = None
        token = None
        table_token = None
        tr_token = None
        left_token = None
        table_dfa.up_tokens = []
        table_lines = None
        tag = None
        text = None
        range_ = None
        r = None
        c = None
        b = None
        t = None
        block_state = None

        if start_line + 2 > end_line:
            return False

        table_token = Token('table_open', 'table', 1)
        table_token.meta = {'sep': None, 'cap': None, 'tr': []}

        table_dfa.set_highest_alphabet(0x10000)
        table_dfa.set_initial_state(0x10100)
        table_dfa.set_accept_states([0x10010, 0x10011, 0x00000])
        table_dfa.set_match_alphabets({
            0x10000: partial(table_caption, state, True),
            0x01000: partial(table_separator, state, True),
            0x00100: partial(table_row, state, True),
            0x00010: partial(table_row, state, True),
            0x00001: partial(table_empty, state, True)
        })
        table_dfa.set_transitions({
            0x10100: {0x10000: 0x00100, 0x00100: 0x01100},
            0x00100: {0x00100: 0x01100},
            0x01100: {0x01000: 0x10010, 0x00100: 0x01100},
            0x10010: {0x10000: 0x00000, 0x00010: 0x10011},
            0x10011: {0x10000: 0x00000, 0x00010: 0x10011, 0x00001: 0x10010}
        })
        if options['headerless']:
            table_dfa.set_initial_state(0x11100)
            table_dfa.update_transition(0x11100, {
                0x10000: 0x01100, 0x01000: 0x10010, 0x00100: 0x01100
            })
            tr_token = Token('tr_placeholder', 'tr', 0)
            tr_token.meta = {}  # avoid trToken.meta.grp throws exception
        if not options['multibody']:
            table_dfa.update_transition(0x10010, {
                0x10000: 0x00000, 0x00010: 0x10010
            })  # 0x10011 is never reached

        def action(_line, _state, _type):
            if _type == 0x10000:
                if table_token.meta['cap'] is not None:
                    table_token.meta['cap'] = table_caption(state, False, _line)
                    table_token.meta['cap']['map'] = [_line, _line + 1]
                    table_token.meta['cap']['first'] = _line == start_line
            elif _type == 0x01000:
                table_token.meta['sep'] = table_separator(state, False, _line)
                table_token.meta['sep']['map'] = [_line, _line + 1]
                tr_token.meta['grp'] |= 0x01
                table_dfa.grp = 0x10
            elif _type == 0x00100 or _type == 0x00010:
                tr_token = Token('tr_open', 'tr', 1)
                tr_token.map = [_line, _line + 1]
                tr_token.meta = table_row(state, False, _line)
                tr_token.meta['type'] = _type
                tr_token.meta['grp'] = table_dfa.grp
                table_dfa.grp = 0x00
                table_token.meta['tr'].append(tr_token)
                
                # Multiline. Merge tr_tokens as an entire multiline tr_token
                if options['multiline']:
                    if tr_token.meta['multiline'] and table_dfa.mtr < 0:
                        table_dfa.mtr = len(table_token.meta['tr']) - 1
                    elif not tr_token.meta['multiline'] and table_dfa.mtr >= 0:
                        # End line of multiline row. merge forward until the marked tr_token
                        token = table_token.meta['tr'][table_dfa.mtr]
                        token.meta['mbounds'] = [tk.meta['bounds'] for tk in table_token.meta['tr'][table_dfa.mtr:]]
                        token.map[1] = tr_token.map[1]
                        table_token.meta['tr'] = table_token.meta['tr'][0:table_dfa.mtr+1] # POTENTIAL POINT OF FAILURE; CHECK;
                        table_dfa.mtr = -1
            elif _type == 0x00001:
                tr_token.meta['grp'] |= 0x01
                table_dfa.grp = 0x10

        table_dfa.set_actions(action)
        
        if not table_dfa.execute(start_line, end_line):
            return False
        
        if len(table_token.meta['tr']) == 0:
            return False
    
        if silent:
            return True
        
        # Last data row cannot be detected. not stored to tr_token outside?
        table_token.meta['tr'][-1].meta['grp'] |= 0x01

        # Second pass: actually push the tokens into `state.tokens`.
        # thead/tbody/th/td open tokens and all closed tokens are generated here;
        # thead/tbody are generally called tgroup; td/th are generally called tcol.

        table_token.map = table_lines = [start_line, 0]
        table_token.block = True
        table_token.level = state.level
        state.level = state.level + 1
        state.tokens.append(table_token)

        if table_token.meta['cap']:
            token = state.push('caption_open', 'caption', 1)
            token.map = table_token.meta['cap']['map']

            # None is possible when the option autolabel is disabled
            if table_token.meta['cap']['label'] is not None:
                token.attrs = {'id': table_token.meta['cap']['label']}
            
            token = state.push('inline', '', 0)
            token.content = table_token.meta['cap']['text']
            token.map = table_token.meta['cap']['map']
            token.children = []

            token = state.push('caption_close', 'caption', -1)

        for tr_token_item in table_token.meta['tr']:
            left_token = Token('td_th_placeholder', '', 0)
            
            # Push in thead/tbody and tr open tokens
            if tr_token_item.meta['grp'] & 0x10:
                tag = 'thead' if tr_token_item.meta['type'] == 0x00100 else 'tbody'
                token = state.push(tag + '_open', tag, 1)
                token.map = table_dfa.tgroup_lines = [tr_token_item.map, 0]
                table_dfa.up_tokens = []
            
            tr_token_item.block = True
            tr_token_item.level = state.level
            state.level += 1
            state.tokens.append(tr_token_item)

            # Push in th/td tokens
            for c in range(len(tr_token_item.meta['bounds'] - 1)):
                text = copy(state.src[tr_token_item.meta['bounds'][c] + 1:tr_token_item.meta['bounds'][c+1]])
                if text == '':
                    table_dfa.colspan = left_token.attrGet('colspan')
                    left_token.attrSet('colspan', 2 if table_dfa.colspan is None else table_dfa.colspan + 1)
                    continue
                if options['rowspan'] and table_dfa.up_tokens[c] and text.strip() == '^^':
                    left_token = Token('td_th_placeholder', '', 0)
                    continue

                tag = 'th' if tr_token_item.meta['type'] == 0x00100 else 'td'
                token = state.push(tag + '_open', tag, 1)
                token.map = tr_token_item['map']
                token.attrs = {}
                
                if table_token.meta['sep']['aligns'][c]:
                    token.attrs['style'] = 'text-align:' + table_token.meta['sep']['aligns'][c]
                
                if table_token.meta['sep']['wraps'][c]:
                    token.attrs['class'] = 'extend'
                
                left_token = table_dfa.up_tokens[c] = token
            
                # Multiline. Join the text and feed into markdown-it blockParser.
                if options['multiline'] and tr_token_item.meta['multiline'] and tr_token_item.meta['mbounds']:
                    # Pad the text with empty lines to ensure the line number mapping is correct
                    text = [''] * tr_token_item.map[0] + [text.rstrip()]
                    for b in range(len(tr_token_item.meta['mbounds'])):
                        # Line with N bounds has cells indexed from 0 to N-2
                        if c > len(tr_token_item.meta['mbounds'][b]) - 2:
                            continue
                        text.extend(copy(state.src[tr_token_item.meta['bounds'][b][c] + 1:tr_token_item.meta['bounds'][b][c+1]]))
                    
                    block_state = StateBlock('\n'.join(text), state.md, state.env, [])
                    block_state.level = tr_token_item.level + 1
                    # Start tokenizing from the actual content (tr_token_item.map[0])
                    state.md.block.tokenize(block_state, tr_token_item.map[0], block_state.lineMax)
                    state.tokens.extend(block_state.tokens)
                else:
                    token = state.push('inline', '', 0)
                    token.content = text.strip()
                    token.map = tr_token_item.map
                    token.level = tr_token_item.level + 1
                    token.children = []
                
                token = state.push(tag + '_close', tag, -1)
            
            # Push in tr and thead/tbody closed tokens
            state.push('tr_close', 'tr', -1)
            if tr_token_item.meta['grp'] & 0x01:
                tag = 'thead' if tr_token_item.meta['type'] == 0x00100 else 'tbody'
                token = state.push(tag + '_close', tag, -1)
                table_dfa.tgroup_lines[1] = tr_token_item.map[1]
        
        table_lines[1] = max(
            table_dfa.tgroup_lines[1],
            table_token.meta['sep'].map[1],
            table_token.meta['cap'].map[1] if table_token.meta['cap'].map else -1
        )

        token = state.push('table_close', 'table', -1)
        state.line = table_lines[1]
        return True
    md.block.ruler.at('table', table, {'alt': ['paragraph', 'reference']})




# def table(state, startLine, endLine, silent):
#     tableDFA = DFA()

#     if (startLine + 2 > endLine):
#         return False

#     tableDFA.set_highest_alphabet(DFA.CAPTION)
#     tableDFA.set_initial_state(DFA.INITIAL_STATE)
#     tableDFA.set_accept_states(DFA.ACCEPT_STATES)
#     tableDFA.set_match_alphabets({
#         DFA.CAPTION: table_caption.bind(this, state, True),
#         DFA.SEPARATOR: table_separator.bind(this, state, True),
#         DFA.HEADER: table_row.bind(this, state, True),
#         DFA.DATA: table_row.bind(this, state, True),
#         DFA.EMPTY: table_empty.bind(this, state, True)
#     })
