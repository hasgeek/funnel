# -*- coding: utf-8 -*-

import re

_strip_re = re.compile(ur'[\'"`‘’“”′″‴]+')
_punctuation_re = re.compile(ur'[\t +!#$%&()*\-/<=>?@\[\\\]^_{|}:;,.…‒–—―]+')

def makename(text, delim=u'-', maxlength=50, filter=None):
    u"""
    Generate a Unicode name slug.

    >>> makename('This is a title')
    u'this-is-a-title'
    >>> makename('Invalid URL/slug here')
    u'invalid-url-slug-here'
    >>> makename('this.that')
    u'this-that'
    >>> makename("How 'bout this?")
    u'how-bout-this'
    >>> makename(u"How’s that?")
    u'hows-that'
    >>> makename(u'K & D')
    u'k-d'
    >>> makename('billion+ pageviews')
    u'billion-pageviews'
    """
    return unicode(delim.join([_strip_re.sub('', x) for x in _punctuation_re.split(text.lower()) if x != '']))
