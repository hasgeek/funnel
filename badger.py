import svgutils.transform as sg
import sys
import qrcode
import qrcode.image.svg
import subprocess
from remotesync import *


def make_badge(space, participant, template):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make("{0}:{1}".format(str(participant.id), participant.key), image_factory=factory)
    img_name = '{0}_{1}_{2}'.format(space.profile.name, space.name, str(participant.id))
    img_path = "{0}.svg".format(img_name)
    img.save(img_path)

    first_name = sg.TextElement(400, 800, participant.fullname.split()[0], size=140, weight="bold")
    last_name = sg.TextElement(400, 900, participant.fullname.split()[1], size=80)
    company = sg.TextElement(400, 1000, participant.company, size=60)
    twitter = sg.TextElement(400, 1100, "@{0}".format(participant.twitter), size=60)
    qr_sg = sg.fromfile(img_path).getroot()
    qr_sg.moveto(470, 1200, scale=15)

    badge_sg = sg.fromfile(badge_template)
    badge_sg.append([first_name, last_name, company, twitter, qr_sg])
    badge_path = '{0}_{1}.svg'.format(img_path, 'badge')
    badge_sg.save(badge_path)

    # inkscape --export-pdf=metarefresh_2015_1.svg_badge.pdf metarefresh_2015_1.svg_badge.svg
    p=subprocess.call(['inkscape', '--export-pdf={0}.pdf'.format(img_name), badge_path])

badge_template = '/home/shreyas/hasgeek/docs/mr_badge2.svg'
make_badge(ProposalSpace.query.first(), Participant.query.first(), badge_template)
