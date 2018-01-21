# -*- coding: utf-8 -*-

# Hey, here is a better way to implement this.
# http://undefinedvalue.com/adding-a-jinja2-filter-with-a-pelican-plugin.html

from copy import copy
from datetime import datetime
from collections import defaultdict
from markdown import Markdown

markdown = Markdown(extensions=['markdown.extensions.extra'])



PREFERENCE = ['News', 'DevOps', 'Security', 'System Design', 'Engineering', 'Infrastructure', 'Performance', 'Unix', 'Tools', 'Unix / Tools', 'Machine Learning', 'Python', 'Protocol', 'Coding Style', 'Database', 'Chicken Soup for the Soul']

def group_verses_into_newsletter(value, current):
    import pelicanconf
    articles = defaultdict(list)
    for verse in value:
        if verse.category != 'verses':
            continue
        if not hasattr(current, 'verse_start') or not hasattr(current, 'verse_end'):
            continue
        if verse.date < datetime.strptime(current.verse_start + ' +0000', '%Y-%m-%d %z'):
            continue
        if verse.date >= datetime.strptime(current.verse_end + ' +0000', '%Y-%m-%d %z'):
            continue
        if not hasattr(verse, 'verse_category'):
            category = ''
        else:
            category = verse.verse_category
        articles[category].append(verse)
    def sort(kv):
        category, verses = kv
        if category in PREFERENCE:
            return PREFERENCE.index(category)
        return 999
    cat_verses = sorted(articles.items(), key=sort)
    return cat_verses

def newsletter_content(value, current):
    from pelican.settings import DEFAULT_CONFIG
    contents = []
    print(current.title)
    if not value:
        return current.content
    for cat, verses in value:
        contents.append('### ' + cat)
        for verse in verses:
            contents.append('* [%s](%s/%s)' % (verse.title, DEFAULT_CONFIG['SITEURL'], verse.url))
        contents.append('')
    html = '\n'.join(contents)
    print(html)
    return html

def md(content, *args):
    return markdown.convert(content)
