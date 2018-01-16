# -*- coding: utf-8 -*-
from funnel.util import extract_twitter_handle

event_ticket_types = [
    {'title': 'SpaceCon', 'ticket_types': ['Conference', 'Combo']},
    {'title': 'SpaceCon workshop', 'ticket_types': ['Workshop', 'Combo']},
]

ticket_list = [{
    'fullname': u'participant{id}'.format(id=unicode(1)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(1)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(1))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(1)),
    'ticket_type': u'Combo',
    'order_no': u'o{id}'.format(id=unicode(1)),
    'status': u'confirmed'
},
    {'fullname': u'participant{id}'.format(id=unicode(2)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(2)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(2))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(2)),
    'ticket_type': u'Workshop',
    'order_no': u'o{id}'.format(id=unicode(2)),
    'status': u'confirmed'
},
    {'fullname': u'participant{id}'.format(id=unicode(3)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(3)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(3))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(3)),
    'ticket_type': u'Conference',
    'order_no': u'o{id}'.format(id=unicode(3)),
    'status': u'confirmed'
}
]

ticket_list2 = [{
    'fullname': u'participant{id}'.format(id=unicode(1)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(1)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(1))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(1)),
    'ticket_type': u'Combo',
    'order_no': u'o{id}'.format(id=unicode(1)),
    'status': u'confirmed'
},
    {'fullname': u'participant{id}'.format(id=unicode(2)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(2)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(2))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(2)),
    'ticket_type': u'Workshop',
    'order_no': u'o{id}'.format(id=unicode(2)),
    'status': u'cancelled'
},
    {'fullname': u'participant{id}'.format(id=unicode(3)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(3)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(3))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(3)),
    'ticket_type': u'Conference',
    'order_no': u'o{id}'.format(id=unicode(3)),
    'status': u'confirmed'
}
]

ticket_list3 = [{
    'fullname': u'participant{id}'.format(id=unicode(1)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(1)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(1))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(1)),
    'ticket_type': u'Combo',
    'order_no': u'o{id}'.format(id=unicode(1)),
    'status': u'confirmed'
},
    {'fullname': u'participant{id}'.format(id=unicode(2)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(2)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(2))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(2)),
    'ticket_type': u'Workshop',
    'order_no': u'o{id}'.format(id=unicode(2)),
    'status': u'cancelled'
},
    {'fullname': u'participant{id}'.format(id=unicode(4)),
    'email': u'participant{id}@gmail.com'.format(id=unicode(4)),
    'phone': u'123',
    'twitter': extract_twitter_handle(u'@p{id}'.format(id=unicode(4))),
    'job_title': u'Engineer',
    'company': u'Acme',
    'city': u'Atlantis',
    'ticket_no': u't{id}'.format(id=unicode(3)),
    'ticket_type': u'Conference',
    'order_no': u'o{id}'.format(id=unicode(3)),
    'status': u'confirmed'
}
]
