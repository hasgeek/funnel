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

from trello import TrelloClient
from funnel import app
from funnel.models import db, Proposal
from baseframe import __


def on_proposal_create_or_update(proposalid):
    """
    """
    with app.test_request_context():
        proposal = Proposal.query.get(proposalid)
        space = proposal.proposal_space
        # Is there a board associated with this proposal's space?
        if space.trello_board_id:
            tlist = get_or_create_trello_list(space)
            create_or_update_proposal_card(proposalid, tlist=tlist)

        else:
            pass


def get_or_create_trello_list(space):
    """
    Returns the trello list object for a given space. Creates it if not available
    """
    api_key = app.config.get('TRELLO_API_KEY')
    api_secret = app.config.get('TRELLO_API_SECRET')
    token = app.config.get('TRELLO_TOKEN')
    token_secret = app.config.get('TRELLO_SECRET')

    client = TrelloClient(api_key=api_key, api_secret=api_secret, token=token, token_secret=token_secret)

    tlist = None
    if space.trello_board_id:
        tboard = client.get_board(space.trello_board_id)
        # Is there a list for the space's updates? If not, create it.
        try:
            tlist = tboard.get_list(space.trello_list_id)
        except:
            tlist = tboard.add_list("Talkfunnel")
            space.trello_list_id = tlist.id
            db.session.add(space)
            db.session.commit()
            # add_missing_proposals_to_list()
    return tlist


def create_or_update_proposal_card(proposalid, tlist=None):
    """
    Adds a Trello card in a list and board for a proposal if possible, updates it if it exists already.
    """
    api_key = app.config.get('TRELLO_API_KEY')
    api_secret = app.config.get('TRELLO_API_SECRET')
    token = app.config.get('TRELLO_TOKEN')
    token_secret = app.config.get('TRELLO_SECRET')

    client = TrelloClient(api_key=api_key, api_secret=api_secret, token=token, token_secret=token_secret)

    proposal = Proposal.query.get(proposalid)
    space = proposal.proposal_space
    # Is there a card for this proposal? If not, create one.

    if proposal.trello_card_id == '':
        if tlist is None:
            tlist = get_or_create_trello_list(space)
        if tlist:
            tcard = tlist.add_card(name=proposal.title, desc=make_card_summary(proposal))
            proposal.trello_card_id = tcard.id
            db.session.add(proposal)
            db.session.commit()
    else:
        # Get card associated with this proposal
        tcard = client.get_card(proposal.trello_card_id)
        if tcard.name is not proposal.title:
            tcard.set_name(proposal.title)
            tcard.comment(text=__(u"Title updated"))
        if tcard.desc is not make_card_summary(proposal):
            tcard.set_decription(make_card_summary(proposal))
            tcard.comment(text=__(u"Description updated"))
        tcard.comment(text=make_changelog(proposal))


def make_changelog(proposal):
    """
    Makes a changelog of what has changed in the proposal
    """
    # TODO: Make a more verbose changelog
    return __(u"Proposal has been updated")


def make_card_summary(proposal):
    """
    Makes a readable summary of the proposal
    """
    return proposal.description_text+"\n\n"+proposal.objective_text


def add_missing_proposals_to_list(space):
    """
    Add cards for all proposals which don't have cards associated with them
    """
    for proposal in space.proposals_all():
        if proposal.trello_card_id is None:
            create_or_update_proposal_card(proposal)


def create_trello_lists(space):
    """
    Creates Trello lists of a space
    """
    pass


def has_trello_lists(space):
    """
    Checks if the space has associated lists for each state of the proposal
    """
    pass


def create_proposal_comment(proposal, comment):
    """
    Adds a comment to the proposal's card if there was a comment added to the proposal
    """
    pass


def update_proposal_comment(proposal, comment):
    """
    Adds a comment to the proposal's card if there was a comment edited on the proposal
    """
    pass
