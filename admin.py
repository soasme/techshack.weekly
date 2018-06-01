#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import itertools
import click
import glob
import sys
import re
import json
import jinja2
import requests
import telegram
import html
from collections import defaultdict
from urllib.parse import unquote
from datetime import datetime, timedelta

TECHSHACK_SIMPLENOTE_TAG = 'techshack'
DATE_PATTERN = re.compile(r'^# Techshack\s+(\d{4}-\d{2}-\d{2})$')
URL_PATTERN = re.compile(r'\* url: (&lt;|<)(.*)(&gt;|>)')
VERSE_TEMPLATE = """Title: {{title}}
Date: {{date}} 00:00
Modified: {{date}} 00:00
Slug: verses/{{uuid}}
Category: verses
Authors: Ju Lin
verse_category: {{category}}

[查看原文]({{url}})

{{content}}
"""


@click.group()
def cli():
    pass


def get_twitter_client():
    # https://github.com/inueni/birdy
    from birdy.twitter import UserClient
    client = UserClient(os.environ.get('TWITTER_API_CONSUMER_KEY'),
            os.environ.get('TWITTER_API_CONSUMER_SECRET'),
            os.environ.get('TWITTER_API_ACCESS_TOKEN'),
            os.environ.get('TWITTER_API_ACCESS_SECRET'))
    return client

def get_twitter_followers_count():
    res = get_twitter_client().api.users.show.get(screen_name='techshackweekly')
    return {'Followers': res.data['followers_count']}

def get_tg_channel_members_count():
    res = requests.get('https://tgwidget.com/widget/count/?id=5a66b26483ba88e7118b4568')
    match = re.search(r'(\d+) members', str(res.content))
    return {'Members': int(match.group(1))}

def get_mailchimp_subscribers_count():
    key = os.environ.get('MAILCHIMP_API_KEY')
    res = requests.get('https://us17.api.mailchimp.com/3.0/',
            auth=('TechshackWeekly', key))
    if res.status_code != 200:
        raise Exception(res.json())
    return {'Subscribers': res.json()['total_subscribers']}

@cli.command()
def update_growth_numbers():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    data = {'Date': today}
    data.update(get_twitter_followers_count())
    data.update(get_tg_channel_members_count())
    data.update(get_mailchimp_subscribers_count())
    with open('%s/Techshack_Weekly_Meta_-_Growth_Stats.tid' % os.environ['DATA_DIR']) as f:
        tiddler = _parse_tiddler(f.read(), raw=True)
        dataset = json.loads(tiddler['text'])
        el = next((t for t in dataset if t['Date'] == today), None)
        if el:
            el.update(data)
        else:
            dataset.append(data)
    for k in tiddler:
        if k != 'text':
            print('%s: %s' % (k, tiddler[k]))
    print('\n')
    print(json.dumps(dataset, indent=4, sort_keys=True))

    # with open('content/stories/0001-growth-of-techshack-weekly.md') as f:
        # content = f.read().strip()
        # tag = '<NEW-STUFF-HERE>'
        # line = ('|%(today)s|%(twitter_followers_count)s|'
            # '%(mailchimp_subscribers_count)s|'
            # '%(telegram_channel_members_count)s|'
            # '%(site_sessions)s|%(site_users)s|%(page_views)s|' % data
        # )
        # content = content.replace(tag, line + '\n' + tag)
        # print(content)

@cli.command()
@click.option('--release/--no-release', default=False)
@click.argument('input', type=click.File('rb'))
def push_to_telegram_channel(release, input):
    # https://core.telegram.org/bots/api#markdown-style
    # Supported style

    # pipenv run python admin.py push_to_telegram_channel /tmp/b.md

    bot = telegram.Bot(os.environ['TELEGRAM_API_TOKEN'])

    if release:
        chat = '@techshack'
    else:
        chat = '@techshackweeklystaging'

    text = input.read().decode('utf-8')

    print(text)
    if len(text) > 4096:
        raise Exception('Text too long.')

    bot.send_message(chat, text=str(text), parse_mode='Markdown')

def _parse_tiddler_header_item(content):
    spliter = content.index(':')
    return [content[:spliter].strip(), content[spliter+1:].strip()]

def _parse_tiddler(content, raw=False):
    lines = content.splitlines()
    meta = dict(_parse_tiddler_header_item(line) for line in itertools.takewhile(lambda l: l.strip(), lines))
    meta['text'] = '\n'.join(itertools.dropwhile(lambda l: l.strip(), lines)).strip()
    if 'ns' not in meta:
        return
    if meta['ns'] == 'techshack-weekly.verse':
        meta['type'] = 'verse'
    elif meta['ns'] == 'techshack-weekly.issue':
        meta['type'] = 'techshack-issue'
    elif raw:
        return meta
    else:
        return
    return meta

@cli.command()
def sync_tiddlers():
    notes = []
    for path in glob.glob('%s/*.tid' % os.environ['DATA_DIR']):
        with open(path) as f:
            tiddler = _parse_tiddler(f.read())
            if tiddler:
                notes.append(tiddler)
    for path in glob.glob('%s/*.md' % os.environ['DATA_DIR']):
        with open('%s.meta' % path) as f:
            tiddler = _parse_tiddler(f.read())
        if tiddler:
            with open(path) as f:
                tiddler['text'] = f.read()
            notes.append(tiddler)

    click.echo(json.dumps(notes, indent=4, ensure_ascii=False))

PREFERENCE = ['News', 'DevOps', 'Security', 'System Design', 'Engineering', 'Infrastructure', 'Performance', 'Unix', 'Tools', 'Unix / Tools', 'Machine Learning', 'Python', 'Protocol', 'Coding Style', 'Database', 'Chicken Soup for the Soul', 'Frontend']

def sort_preference(kv):
    category, _ = kv
    if category in PREFERENCE:
        return PREFERENCE.index(category)
    return 999

def _gen_issue_text(data, iss):
    text = []
    issue = iss['issue']
    text.append('%s [前往查看](https://www.soasme.com/techshack.weekly/issues/%s.html)\n\n' % (iss['text'], issue))
    verses = [note for note in data if note.get('type') == 'verse' and iss['start'] <= note['date'] < iss['end']]
    cat_verses = defaultdict(list)
    for verse in verses:
        cat_verses[verse['category']].append(verse)
    verses = sorted(cat_verses.items(), key=sort_preference)
    for cat, notes in verses:
        text.append('%s\n' % cat)
        for note in notes:
            url = 'https://www.soasme.com/techshack.weekly/verses/%s.html' % note['key']
            text.append('- [%s](%s)\n' % (note['title'], url))
    return '\n'.join(text)

@cli.command()
def dump_from_json():
    with open('default.json') as f:
        data = json.load(f)
        assert len(data)
        for note in data:
            if 'title' in note and 'date' in note and 'key' in note \
                    and 'category' in note and 'url' in note \
                    and 'text' in note \
                    and 'type' in note and note['type'] == 'verse':
                verse = """Title: %(title)s
Date: %(date)s 00:00
Modified: %(date)s 00:00
Slug: verses/%(key)s
Category: verses
Authors: Ju Lin
verse_category: %(category)s

[查看原文](%(url)s)

%(text)s""" % note
                with open('content/verses/%s.md' % note['key'], 'w') as w:
                    w.write(verse)
            elif 'type' in note and note['type'] == 'techshack-issue' \
                    and 'start' in note and 'end' in note \
                    and 'publish' in note and 'issue' in note:
                note['_content'] = _gen_issue_text(data, note)
                note['title'] = note.get('title') or 'Techshack Weekly 第 %s 期' % note['issue']
                issue = """Title: Techshack Weekly 第 %(issue)s 期
Date: %(publish)s 00:00
Modified: %(publish)s 00:00
Slug: issues/%(issue)s
Category: issues
Authors: Ju Lin
Summary: %(text)s
verse_start: %(start)s
verse_end: %(end)s

%(_content)s""" % note
                with open('content/issues/%s.md' % note['issue'], 'w') as w:
                    w.write(issue)


@cli.command()
@click.argument('issue')
def tg_issue(issue):
    with open('default.json') as f:
        data = json.load(f)
        iss = next(note for note in data if note.get('issue') == issue)
        click.echo(_gen_issue_text(data, iss))

if __name__ == '__main__':
    cli()
