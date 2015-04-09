import sys
from funnel.models import (Profile, ProposalSpace)
from shell import *
init_for('dev')

if __name__ == '__main__':
    profile = Profile.query.filter_by(name=sys.argv[1]).first()
    space = ProposalSpace.query.filter_by(name=sys.argv[2]).filter_by(profile_id=profile.id).first()
    print "Printing Badges..."
    for p in space.participants.first():
        p.make_badge(space)
    print "Done"
