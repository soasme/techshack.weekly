#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import click
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
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

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


GA_SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
def get_ga_stats(date):
    # https://developers.google.com/analytics/devguides/reporting/core/v4/quickstart/service-py
    credentials = ServiceAccountCredentials.from_json_keyfile_name(os.environ['GA_KEY_FILE_LOCATION'], GA_SCOPES)
    analytics = build('analyticsreporting', 'v4', credentials=credentials)
    response = analytics.reports().batchGet(
        body={
            'reportRequests': [
            {
            # https://ga-dev-tools.appspot.com/account-explorer/
            'viewId': os.environ['GA_VIEW_ID'],
            'dateRanges': [{'startDate': date, 'endDate': date}],
            # https://developers.google.com/analytics/devguides/reporting/core/dimsmets
            'metrics': [{'expression': 'ga:sessions'}, {'expression': 'ga:users'}, {'expression': 'ga:pageviews'}],
            #'dimensions': [{'name': 'ga:country'}]
            }]
        }
    ).execute()
    reports = response.get('reports', [])
    assert len(reports) == 1, reports
    report = reports[0]
    return dict(zip(['site_sessions', 'site_users', 'page_views'], report['data']['rows'][0]['metrics'][0]['values']))

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
    return {'twitter_followers_count': res.data['followers_count']}

def get_tg_channel_members_count():
    res = requests.get('https://tgwidget.com/widget/count/?id=5a66b26483ba88e7118b4568')
    match = re.search(r'(\d+) members', str(res.content))
    return {'telegram_channel_members_count': int(match.group(1))}

def get_mailchimp_subscribers_count():
    key = os.environ.get('MAILCHIMP_API_KEY')
    res = requests.get('https://us17.api.mailchimp.com/3.0/',
            auth=('TechshackWeekly', key))
    if res.status_code != 200:
        raise Exception(res.json())
    return {'mailchimp_subscribers_count': res.json()['total_subscribers']}

@cli.command()
def update_growth_numbers():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    data = {'today': today}
    data.update(get_ga_stats(today))
    data.update(get_twitter_followers_count())
    data.update(get_tg_channel_members_count())
    data.update(get_mailchimp_subscribers_count())
    with open('content/stories/0001-growth-of-techshack-weekly.md') as f:
        content = f.read()
        tag = '<NEW-STUFF-HERE>'
        line = ('|%(today)s|%(twitter_followers_count)s|'
            '%(mailchimp_subscribers_count)s|'
            '%(telegram_channel_members_count)s|'
            '%(site_sessions)s|%(site_users)s|%(page_views)s|' % data
        )
        content = content.replace(tag, line + '\n' + tag)
        print(content)

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

@cli.command()
def sync_zetanote():
    with open('default.json') as f:
        data = json.load(f)
        for note in data['notes'].values():
            if 'title' in note and 'date' in note and 'key' in note \
                    and 'category' in note and 'url' in note \
                    and 'text' in note and note['title'] != 'No-title' \
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
                issue = """Title: 第 %(issue)s 期
Date: %(publish)s 00:00
Modified: %(publish)s 00:00
Slug: issues/%(issue)s
Category: issues
Authors: Ju Lin
Summary: Techshack Weekly 第 %(issue)s 期
verse_start: %(start)s
verse_end: %(end)s

%(text)s""" % note
                with open('content/issues/%s.md' % note['issue'], 'w') as w:
                    w.write(issue)

PREFERENCE = ['News', 'DevOps', 'Security', 'System Design', 'Engineering', 'Infrastructure', 'Performance', 'Unix', 'Tools', 'Unix / Tools', 'Machine Learning', 'Python', 'Protocol', 'Coding Style', 'Database', 'Chicken Soup for the Soul', 'Frontend']

@cli.command()
@click.argument('issue')
def tg_issue(issue):
    def sort(kv):
        category, _ = kv
        if category in PREFERENCE:
            return PREFERENCE.index(category)
        return 999
    with open('default.json') as f:
        data = json.load(f)
        iss = next(note for note in data['notes'].values() if note.get('issue') == issue)
        click.echo('*%s*\n\n%s [前往查看](https://www.soasme.com/techshack.weekly/issues/%s.html)\n\n' % (issue, iss['text'], issue))
        verses = [note for note in data['notes'].values() if note.get('type') == 'verse' and iss['start'] <= note['date'] < iss['end']]
        cat_verses = defaultdict(list)
        for verse in verses:
            cat_verses[verse['category']].append(verse)
        verses = sorted(cat_verses.items(), key=sort)
        for cat, notes in verses:
            click.echo('%s\n' % cat)
            for note in notes:
                url = 'https://www.soasme.com/techshack.weekly/verses/%s.html' % note['key']
                click.echo('- [%s](%s)\n' % (note['title'], url))
        #print(iss, verses)

if __name__ == '__main__':
    cli()
