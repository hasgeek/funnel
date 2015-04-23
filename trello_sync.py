import sys
import requests
from urlparse import urlparse
from datetime import datetime
from funnel import init_for
from funnel.models import (db, Proposal, PROPOSALSTATUS, ProposalSpace, Profile)
from funnel import app

import logging
logging.basicConfig(filename='trello_sync.log', level=logging.DEBUG)


def find_url_in_text(text, pattern):
    """ parses the text, returns the first url that
        matches the given pattern
    """
    url_matches = [word
                   for word in text.split()
                   if urlparse(pattern).netloc in word]
    return url_matches[0] if url_matches else None


def get_id_from_permalink(permalink, sep='-', pos=0):
    """ extracts the last segment of permalink
        returns the id as an int
        Eg: 'https://rootconf.talkfunnel.com/2015/42-x-y' -> '42'
    """
    last_segment = urlparse(permalink).path.split('/')[-1]
    return int(last_segment.split(sep)[pos]) if last_segment else None


def update_proposals(proposal_space, l, status):
    """ Get cards for a given list id from Trello,
        retrieve corresponding proposal, and update status if
        found to be changed on Trello
    """
    cards_url = "{base_url}/lists/{list_id}/cards?key={key}&token={token}"\
        .format(base_url=app.config.get('TRELLO_API_ENDPOINT'),
                list_id=l.get('id'),
                key=app.config.get('TRELLO_KEY'),
                token=app.config.get('TRELLO_TOKEN'))
    cards = requests.get(cards_url).json()
    for card in cards:
        proposal_url = find_url_in_text(card.get('desc'), proposal_space.url_for('view'))
        if proposal_url:
            url_id = get_id_from_permalink(proposal_url)
            proposal = Proposal.query.filter_by(proposal_space=proposal_space, url_id=url_id).first()
            if proposal:
                if proposal.status != status:
                    proposal.status = status
                    db.session.add(proposal)
            else:
                logging.warning("No proposal called {0} found".format(card.get('name').encode('utf-8')))
        else:
            logging.warning("No proposal link for {0} in description".format(card.get('name').encode('utf-8')))
    db.session.commit()


def sync_status_updates_from_trello(proposal_space, trello_board_id):
    trello_lists_url = "{base_url}/boards/{board_id}/lists?key={key}&token={token}"\
                       .format(base_url=app.config.get('TRELLO_API_ENDPOINT'),
                               board_id=trello_board_id,
                               key=app.config.get('TRELLO_KEY'),
                               token=app.config.get('TRELLO_TOKEN'))

    lists = requests.get(trello_lists_url)
    if not lists.ok:
        return False, "Could not connect to the Trello board - {0}.".format(trello_board_id)

    # Makes a list of dictionaries, collating PROPOSALSTATUS enums
    # with the corresponding lists on Trello
    # Eg: lists which have "Confirmed" in their labels will be mapped with
    # the appropriate enum in PROPOSALSTATUS, which in this case, is 2
    status_lists = [{'list': l, 'status': key_label[0]}
                    for key_label in PROPOSALSTATUS.items()
                    for l in lists.json()
                    if key_label[1].lower() in l.get('name').lower().split()]

    for status_list in status_lists:
        update_proposals(proposal_space, status_list.get('list'), status_list.get('status'))
    return True, "Synchronized {0} with Trello at {1}".format(proposal_space.url_for('view'), str(datetime.now()))

if __name__ == '__main__':
    # python trello_sync.py <env> <profile name> <proposal space name> <trello board id>
    # Eg: python trello_sync.py dev rootconf 2015 xxx
    init_for(sys.argv[1])
    app.test_request_context().push()
    space = ProposalSpace.query.join(Profile)\
        .filter(Profile.name == sys.argv[2], ProposalSpace.name == sys.argv[3]).first()
    result = sync_status_updates_from_trello(space, sys.argv[4])
    if result[0]:
        logging.info(result[1])
    else:
        logging.warning(result[1])
