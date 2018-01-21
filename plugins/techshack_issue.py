from pelican import signals
from copy import copy
from datetime import datetime
from collections import defaultdict
from markdown import Markdown

markdown = Markdown(extensions=['markdown.extensions.extra'])


PREFERENCE = ['News', 'DevOps', 'Security', 'System Design', 'Engineering', 'Infrastructure', 'Performance', 'Unix', 'Tools', 'Unix / Tools', 'Machine Learning', 'Python', 'Protocol', 'Coding Style', 'Database', 'Chicken Soup for the Soul']



def add_filter(pelican):
    """Add age_in_days filter to Pelican."""
    def group_verses_into_newsletter(value, current):
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
        contents = []
        contents.append(current.content)
        for cat, verses in value:
            contents.append('### ' + cat)
            for verse in verses:
                contents.append('* [%s](%s/%s)' % (verse.title, pelican.settings['SITEURL'], verse.url))
            contents.append('')
        html = '\n'.join(contents)
        return html

    def md(content, *args):
        return markdown.convert(content)

    pelican.env.filters.update({
        'newsletter_verses': group_verses_into_newsletter,
        'newsletter_content':newsletter_content,
        'md': md,
    })

def register():
    signals.generator_init.connect(add_filter)
