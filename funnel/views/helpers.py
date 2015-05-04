# -*- coding: utf-8 -*-

from pytz import timezone as pytz_timezone, utc
from datetime import datetime
import qrcode
import qrcode.image.svg


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp)/1000, from_tz, to_tz)


def localize_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(date, from_tz=utc, to_tz=utc):
    if from_tz and to_tz:
        if isinstance(from_tz, basestring):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, basestring):
            to_tz = pytz_timezone(to_tz)
        return from_tz.localize(date).astimezone(to_tz).replace(tzinfo=None)
    return date


def split_name(fullname):
    """ Splits a given fullname into two parts
        a first name, and a concanetated last name.
        Eg: "ABC DEF EFG" -> ("ABC", "DEF EFG")
    """
    name_splits = fullname.split()
    return name_splits[0], " ".join([s for s in name_splits[1:]])


def format_twitter(twitter):
    return "@{0}".format(twitter) if twitter else ""


def file_contents(path):
    """ Returns contents of a given file path
    """
    file = open(path)
    content = file.read()
    file.close()
    return content


def make_qrcode(data, path):
    """ Makes a QR code with a given path and returns the raw svg
        Data Format is id:key. Eg: 1:xxxxxxxx
    """
    try:
        qrcode_svg = file_contents(path)
    except:
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(data, image_factory=factory)
        img.save(path)
        qrcode_svg = file_contents(path)
    return qrcode_svg
