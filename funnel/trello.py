"""
Provides methods to integrate with Trello.

Workflow:
1. Create a list for the board.
TODO: Add the `trello_board_id` and `trello_list_name` columns to `proposal_space`.

2. When a proposal is created on Talkfunnel, a card is created for the the proposal with
the name of the proposal.
TODO: Add a `trello_card_id` column to `proposal`.
@event.listens_for(Proposal, 'after_create')
def on_create(mapper, connection, target):
    pass

3. When a proposal is updated on Talkfunnel, the card is updated with a comment.
Eg: Proposal was updated by Ms X, or Mr Y posted a comment.
@event.listens_for(Proposal, 'after_update')
def on_update(mapper, connection, target):
    pass
"""
# base_url = 'https://api.trello.com/1'
# token = app.config.get('TRELLO_ACCESS_TOKEN')
# key = app.config.get('TRELLO_ACCESS_KEY')

def get_cards_url(list_id):
    return '{base_url}/lists/{list_id}/cards?key={key}&token={token}'.format(base_url=base_url, key=key, token=token, list_id=list_id)


def get_lists_url(board_id):
    return '{board}/boards/{board_id}/lists?key={key}&token={token}'.format(key=key, token=token, board_id=board_id)

def create_list(board_id, name='Talkfunnel'):
    """Creates a list on Trello given a board_id"""
    # requests.post(get_lists_url(board_id), {'name': name, 'idList': list_id})
    pass

def create_card(name, list_id):
    """Creates a card on Trello given a list_id and a name"""
    # requests.post(get_cards_url(board_id), {'name': name, 'idList': list_id})
    pass

def add_comment(comment, card_id):
    """Adds a comment to a card"""
    pass

def get_card_id(name, board_id):
    """Returns the card id given the name and board_id"""
    pass
