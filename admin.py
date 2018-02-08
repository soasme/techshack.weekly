#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import click
import re
import jinja2
import requests
import telegram
from datetime import datetime, timedelta
from simplenote import Simplenote
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

TECHSHACK_SIMPLENOTE_TAG = 'techshack'
DATE_PATTERN = re.compile(r'^# Techshack\s+(\d{4}-\d{2}-\d{2})$')
URL_PATTERN = re.compile(r'\* url: <(.*)>')
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

sn = Simplenote(username=os.environ.get('SIMPLENOTE_USER'),
                password=os.environ.get('SIMPLENOTE_PASS'))


@click.group()
def cli():
    pass


def _parse_simplenote_note(content):
    lines = content.splitlines()

    def _is_verses_hint(ctx, line):
        return line.strip() == '---'

    def _is_uuid_hint(ctx, line):
        return not ctx.get('uuid') and line.strip().startswith('* uuid:')

    def _parse_uuid(ctx, line):
        assert _is_uuid_hint(ctx, line), 'not a uuid hint line.'
        return line.replace('* uuid:', '').strip()

    def _is_date_hint(ctx, line):
        return DATE_PATTERN.search(line)

    def _parse_date(ctx, line):
        assert _is_date_hint(ctx, line)
        match = DATE_PATTERN.search(line)
        assert match, 'no matching date: %s' % line
        return match.group(1)

    def _is_url_hint(ctx, line):
        return not ctx.get('url') and line.startswith('* url:')

    def _parse_url(ctx, line):
        assert _is_url_hint(ctx, line)
        match = URL_PATTERN.search(line)
        assert match, 'no matching url'
        return match.group(1)

    def _is_title_hint(ctx, line):
        return not ctx.get('title') and line.startswith('* title:')

    def _parse_title(ctx, line):
        assert _is_title_hint(ctx, line)
        return line.replace('* title:', '').strip()

    def _is_category_hint(ctx, line):
        return not ctx.get('category') and line.startswith('* category:')

    def _parse_category(ctx, line):
        assert _is_category_hint(ctx, line)
        return line.replace('* category:', '').strip()

    def _is_hint(ctx, line):
        return 'content' not in ctx

    def _is_hint_end(ctx, line):
        return 'uuid' in ctx and 'url' in ctx and not line

    def _is_valid_ctx(ctx):
        return 'uuid' in ctx and 'date' in ctx and 'url' in ctx and 'content' in ctx



    ctx = {}

    for line in lines:
        if _is_verses_hint(ctx, line): # start parse verse
            if _is_valid_ctx(ctx):
                yield {'date': ctx['date'], 'uuid': ctx['uuid'],
                       'url': ctx['url'], 'title': ctx.get('title'),
                       'category': ctx.get('category'),
                       'content': '\n'.join(ctx['content'])}
            if 'date' not in ctx:
                break # Invalid post
            ctx = {'date': ctx['date']}
        elif _is_hint(ctx, line): # parse verse metadata
            if _is_date_hint(ctx, line):
                ctx['date'] = _parse_date(ctx, line)
            elif _is_uuid_hint(ctx, line):
                ctx['uuid'] = _parse_uuid(ctx, line)
            elif _is_url_hint(ctx, line):
                ctx['url'] = _parse_url(ctx, line)
            elif _is_title_hint(ctx, line):
                ctx['title'] = _parse_title(ctx, line)
            elif _is_category_hint(ctx, line):
                ctx['category'] = _parse_category(ctx, line)
            elif _is_hint_end(ctx, line):
                ctx.setdefault('content', [])
        else: # parse verse content
            ctx['content'].append(line)

    if _is_valid_ctx(ctx):
        yield {'date': ctx['date'], 'uuid': ctx['uuid'],
                'url': ctx['url'], 'title': ctx.get('title'),
                'category': ctx['category'],
                'content': '\n'.join(ctx['content'])}


def _generate_verse(verse):

    def _is_valid_verse(verse):
        return verse.get('title') and verse.get('content') and \
                verse.get('uuid') and verse.get('date')

    if not _is_valid_verse(verse):
        print('WARNING: invalid verse: %s' % verse)
        return

    filename = 'content/verses/%s.md' % verse['uuid']
    with open(filename, 'w') as f:
        markdown = jinja2.Template(VERSE_TEMPLATE).render(verse)
        f.write(markdown)
        print('>>>>>>>>> Generating Verse %s <<<<<<<<<<' % filename)
        print(markdown)


@cli.command()
@click.option('--since', help='Format: YYYY-MM-DD')
def import_simplenote(since):
    notes, status = sn.get_note_list(since=since, tags=[TECHSHACK_SIMPLENOTE_TAG])
    assert status != -1, 'Get techshack simplenote notes failed.'
    for _note in notes:
        note, status = sn.get_note(_note['key'])
        assert status != -1, 'Get techshack simplenote note {} failed.'.format(_note['key'])
        for verse in _parse_simplenote_note(note['content']):
            _generate_verse(verse)

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


if __name__ == '__main__':
    cli()
