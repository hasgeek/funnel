from funnel import *
from funnel.models import *
rootconf = ProposalSpace.query.filter_by(title='Fifthelephant 2017').first()
rootconf_participants = Participant.query.filter_by(proposal_space=rootconf).all()
import csv
with open('rootconf_2016_attendees.csv', 'w') as csvfile:
    fieldnames = ['fullname', 'email', 'phone', 'twitter', 'job_title', 'company', 'city']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for p in rootconf_participants:
        row = {}
        row['fullname'] = p.fullname
        row['email'] = p.email
        row['phone'] = p.phone
        row['twitter'] = p.twitter
        row['job_title'] = p.job_title
        row['company'] = p.company
        row['city'] = p.city
        writer.writerow(row)