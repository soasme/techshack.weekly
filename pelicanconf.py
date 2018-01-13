#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Ju Lin'
SITENAME = 'Techshack Weekly'
SITEURL = 'http://127.0.0.1:8000'

PATH = 'content'

TIMEZONE = 'UTC'

DEFAULT_LANG = 'zh'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/%s.atom.xml'
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (
    # ('SRE Weekly', 'https://sreweekly.com'),
    # ('Monitoring Weekly', 'https://weekly.monitoring.love'),
)

# Social widget
SOCIAL = (('Twitter', 'https://twitter.com/TechshackWeekly'),
        ('Facebook', 'https://facebook.com/techshack.weekly'),)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

GOOGLE_ANALYTICS = 'UA-36183732-2'

THEME = 'themes/default'
