import svgutils.transform as sg
import sys
import qrcode
import qrcode.image.svg
import subprocess
from remotesync import *


def make_badge(space, participant):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make("{0}:{1}".format(str(participant.id), participant.key), image_factory=factory)
    img_name = '{0}_{1}_{2}'.format(space.profile.name, space.name, str(participant.id))
    img_path = "qrcodes/{0}.svg".format(img_name)
    img.save(img_path)

    fields = []
    name_splits = participant.fullname.split()
    first_name = name_splits[0]
    last_name = "".join([s for s in name_splits[1:]])
    fields.append(sg.TextElement(400, 300, first_name, size=140, weight="bold"))
    if last_name:
        fields.append(sg.TextElement(400, 400, last_name, size=80))
    if participant.company:
        fields.append(sg.TextElement(400, 500, participant.company, size=60))
    if participant.twitter:
        fields.append(sg.TextElement(400, 600, "@{0}".format(participant.twitter), size=60))
    qr_sg = sg.fromfile(img_path).getroot()
    qr_sg.moveto(400, 650, scale=15)
    fields.append(qr_sg)

    # badge_sg = sg.fromfile(badge_template)
    badge_sg = sg.SVGFigure("50cm", "30cm")
    badge_sg.append(fields)
    badge_path = 'badge_svgs/{0}_{1}.svg'.format(img_name, 'badge')
    badge_sg.save(badge_path)

    # inkscape --export-pdf=metarefresh_2015_1.svg_badge.pdf metarefresh_2015_1.svg_badge.svg
    subprocess.call(['inkscape', '--export-pdf=badges/{0}.pdf'.format(img_name), badge_path])

# make_badge(ProposalSpace.query.first(), Participant.query.first())

for p in Participant.query.all():
    make_badge(ProposalSpace.query.first(), p)
