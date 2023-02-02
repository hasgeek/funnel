# class DFA:
#     def __init__(self):
#         # alphabets are encoded by numbers in 16^N form, presenting its precedence
#         self.__highest_alphabet__ = 0x0
#         self.__match_alphabets__ = {}
#         # states are union (bitwise OR) of its accepted alphabets
#         self.__initial_state__ = 0x0
#         self.__accept_states__ = {}
#         # transitions are in the form: {prev_state: {alphabet: next_state}}
#         self.__transitions__ = {}
#         # actions take two parameters: step (line number), prev_state and alphabet
#         self.__actions__ = {}

#     # setters

#     def set_highest_alphabet(self, alphabet):
#         self.__highest_alphabet__ = alphabet

#     def set_match_alphabets(self, matches):
#         self.__match_alphabets__ = matches

#     def set_initial_state(self, initial):
#         self.__initial_state__ = initial

#     def set_accept_states(self, accepts):
#         for i in range(len(accepts)):
#             self.__accept_states__[accepts[i]] = True

#     def set_transitions(self, transitions):
#         self.__transitions__ = transitions

#     def set_actions(self, actions):
#         self.__actions__ = actions

#     def update_transition(self, state, alphabets):
#         self.__transitions__[state] = {**(self.__transitions__.get(state) or {}), **alphabets}

#     # methods

#     def execute(self, start, end):
#         state, step, alphabet = self.__initial_state__, start, self.__highest_alphabet__
#         while state and step < end:
#             while alphabet > 0x0:
#                 if (state & alphabet) and self.__match_alphabets__[alphabet](step, state, alphabet):
#                     break
#                 alphabet >>= 4
#             self.__actions__(step, state, alphabet)
#             if alphabet == 0x0:
#                 break
#             state = self.__transitions__.get(state, {}).get(alphabet, 0x0)
#         return state in self.__accept_states__

class DFA:
    CAPTION = 0x10000
    SEPARATOR = 0x01000
    HEADER = 0x00100
    DATA = 0x00010
    EMPTY = 0x00001
    INITIAL_STATE = 0x10100
    ACCEPT_STATES = [0x10010, 0x10011, 0x00000]

    def __init__(self):
        self.grp = 0x0
        self.mtr = -1
        self.tgroup_lines = None
        self.colspan = None
        self.up_tokens = []
        self._highest_alphabet = 0x0
        self._match_alphabets = {}
        self._initial_state = self.INITIAL_STATE
        self._accept_states = set(self.ACCEPT_STATES)
        self._transitions = {}
        self._actions = {}

    def set_highest_alphabet(self, alphabet):
        self._highest_alphabet = alphabet

    def set_match_alphabets(self, matches):
        self._match_alphabets = matches

    def set_initial_state(self, initial):
        self._initial_state = initial

    def set_accept_states(self, accepts):
        self._accept_states = set(accepts)

    def set_transitions(self, transitions):
        self._transitions = transitions

    def set_actions(self, actions):
        self._actions = actions

    def update_transition(self, state, alphabets):
        self._transitions[state] = {**(self._transitions.get(state) or {}), **alphabets}

    def execute(self, start, end):
        state, step, alphabet = self._initial_state, start, self._highest_alphabet
        while state and step < end:
            while alphabet > 0x0:
                if (state & alphabet) and self._match_alphabets[alphabet](step):
                    break
                alphabet = alphabet >> 4
            self._actions(step, state, alphabet)
            if alphabet == 0x0:
                break
            state = self._transitions.get(state, {}).get(alphabet, 0x0)
        return state in self._accept_states