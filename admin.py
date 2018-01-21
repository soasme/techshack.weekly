#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import click
import re
import jinja2
from datetime import datetime, timedelta
from simplenote import Simplenote

TECHSHACK_SIMPLENOTE_TAG = 'techshack'
DATE_PATTERN = re.compile(r'^# Techshack (\d{4}-\d{2}-\d{2})$')
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


if __name__ == '__main__':
    cli()
