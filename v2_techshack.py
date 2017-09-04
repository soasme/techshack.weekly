#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import re
import argparse
import glob
import os
import json
from configparser import ConfigParser
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4
from functools import partial
from itertools import groupby, takewhile

import mistune
from pony import orm
from slackbot.bot import Bot
from slackbot.bot import respond_to
from dropbox import Dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError as DropboxApiError, AuthError as DropboxAuthError
from jinja2 import Template

with open('template.html') as f:
    SITE_TEMPLATE = f.read()

DEFAULT_CONFIGS = ['/etc/techshack.io/env', './.env']

config_parser = ConfigParser()
config_parser.read(next(f for f in DEFAULT_CONFIGS if os.path.exists(f)))
config = partial(config_parser.get, 'techshackd')

db = orm.Database()

class Stanza(db.Entity):

    id = db.PrimaryKey(str)
    created = db.Required(str)
    ref = db.Required(str)
    thoughts = db.Required(str)
    tags = db.Required(str)

    @property
    def date(self):
        return self.created[:10]

    @property
    def ref_url(self):
        return ref[1:-1] if ref.startswith('<') and ref.endswith('>') else '#'

    @property
    def html_thoughts(self):
        return markdown(re.sub(r'<(.*)>', r'<a href="\1">\1</a>', thoughts))

db.bind(provider='sqlite', filename=config('STANZA_FILE_PATH'), create_db=True)
db.generate_mapping(create_tables=True)

class MarkdownRenderer(mistune.Renderer):

    def codespan(self, text):
        return '<code>%s</code>' % mistune.escape(text.rstrip(), smart_amp=True)

def markdown(text):
    return mistune.Markdown(renderer=MarkdownRenderer())(text)

@orm.db_session
def get_stanzas():
    return takewhile(
        lambda el: (el[0], [s for s in el[1] if s.tags and s.thoughts])
        groupby(Stanza.select().order_by(Stanza.created), lambda s: s.date)
    )


@orm.db_session
def get_stanzas_by_date(date):
    return orm.select(s for s in Stanza if date in s.created)[:]

@orm.db_session
def get_stanza(uuid):
    return Stanza.get(id=uuid)

@orm.db_session
def create_stanza(ref):
    stanza = Stanza(id=str(uuid4()),
           created=datetime.utcnow().isoformat() + '+0000',
           ref=ref, thoughts='', tags='')
    return stanza.id

@orm.db_session
def set_stanza_thoughts(uuid, thoughts):
    stanza = get_stanza(uuid)
    stanza.thoughts = thoughts

@orm.db_session
def set_stanza_tags(uuid, tags):
    stanza = get_stanza(uuid)
    stanza.tags = tags.replace(',', '|')

def format_stanza(stanza):
    return str(stanza)

def start_stanza_session(uuid):
    with open('/tmp/techshack.io.stanza.session', 'w') as f:
        f.write(uuid)

def destroy_stanza_session():
    if os.path.exists('/tmp/techshack.io.stanza.session'):
        os.remove('/tmp/techshack.io.stanza.session')

def get_stanza_session():
    if os.path.exists('/tmp/techshack.io.stanza.session'):
        with open('/tmp/techshack.io.stanza.session', 'r') as f:
            return f.read()

def render_template(template, context):
    return Template(template).render(**context)

HTML_CONTEXT = {
    'slogan': '不要停止技术阅读!'
    'title': 'Tech Shack',
    'jumbotron_text': '不要停止技术阅读!',
    'author': 'Ju Lin <soasme@gmail.com>',
    'program_name': "Tech Shack",
}

def render_stanza_page(**external_context):
    context = HTML_CONTEXT.copy()
    context.update(external_context)
    render_template(SITE_TEMPLATE, context)

def ping(message):
    message.reply('pong')

def show_stanza(message, uuid):
    stanza = get_stanza(uuid)
    if not stanza:
        message.reply('stanza %s not found' % uuid)
    else:
        message.reply(format_stanza(stanza))

def save_stanza(message, uuid):
    uuid = create_stanza(url)
    start_stanza_session(uuid)
    message.reply('Start editing %s' % uuid)

def edit_stanza(message, uuid):
    if get_stanza(uuid):
        start_stanza_session(uuid)
        message.reply('Start editing %s' % uuid)
    else:
        message.reply('Stanza %s not found' % uuid)

def extract_stanzas_tags(stanzas):
    return set(s.tags.split('|') for s in stanzas)

def stop_editing_stanza(message):
    uuid = get_stanza_session()
    if uuid:
        destroy_stanza_session()
        message.reply('Quit editing %s' % uuid)
        message.reply(format_stanza(get_stanza(uuid)))
    else:
        message.reply('No session found.')

def set_stanza_thoughts_to_dat(message, thoughts):
    uuid = get_stanza_session()
    if uuid:
        stanza = get_stanza(uuid)
        if stanza:
            set_stanza_thoughts(uuid, thoughts)
            message.reply('Done')
        else:
            destroy_stanza_session()
            message.reply('Stanza %s not found' % uuid)
    else:
        message.reply('No session found.')

def set_stanza_tags_to_dat(message, tags)
    uuid = get_stanza_session()
    if uuid:
        stanza = get_stanza(uuid)
        if stanza:
            set_stanza_tags(uuid, tags)
            message.reply('Done')
        else:
            destroy_stanza_session()
            message.reply('Stanza %s not found' % uuid)
    else:
        message.reply('No session found.')

SLACKBOT_COMMANDS = [
    # name, pattern, mode
    ('ping', 'ping', re.IGNORECASE),
    ('show_stanza', 'show stanza (.*)', re.IGNORECASE),
    ('save_stanza', 'save stanza (.*)', re.IGNORECASE),
    ('edit_stanza', 'edit stanza (.*)', re.IGNORECASE),
    ('stop_editing_stanza', 'done stanza', re.IGNORECASE),
    ('set_stanza_thoughts_to_dat', 'thoughts (.*)', re.IGNORECASE | re.DOTALL),
    ('set_stanza_tags_to_dat', 'tags (.*)', re.IGNORECASE),
]

def load_slackbot_commands():
    for name, pattern, mode:
        respond_to(pattern, mode)(globals()[name])

def configure_slackbot():
    os.environ['SLACKBOT_API_TOKEN'] = config('SLACKBOT_API_TOKEN')

def prog_slackbot(args, options):
    """Run slackbot. """
    configure_slackbot()
    load_slackbot_commands()
    Bot().run()

def publish_stanza(date, stanzas, path):
    with open(os.path.join(config('HTML_PATH'), path), 'w') as f:
        f.write(render_stanza_page(date=date, stanzas=stanzas))

def publish_stanza_post(date, stanzas):
    publish_stanza(date, stanzas, 'stanza-%s.html' % date)

def publish_index_post():
    files = sorted(glob.glob('%s/stanza-*.html'))
    publish_stanza(re) # TODO find first and make it `index.html`

def prog_publish(args, options):
    """Publish stanzas as static website."""
    for date, stanzas in get_stanzas():
        publish_stanza(date, stanzas)


def prog_backup(args, options):
    """Backup database to dropbox."""
    with open(config('STANZA_FILE_PATH'), 'rb') as f:
        dbx = dropbox.Dropbox(config('DROPBOX_API_TOKEN'))
        try:
            dbx.users_get_current_account()
        except DropboxAuthError as err:
            sys.exit("ERROR: Invalid access token; try re-generating one.")
        try:
            dbx.files_upload(f.read(), config('REMOTE_BACKUP_STANZA_FILE_PATH'),
                    mode=WriteMode('overwrite'))
        except DropboxApiError as err:
            if (err.error.is_path() and err.error.get_path().error.is_insufficient_space()):
                sys.exit("ERROR: insufficient dropbox space.")
            elif err.user_message_text:
                sys.exit("ERROR: %s" % err.user_message_text)
            else:
                print(err); sys.exit()


def prog_tweet(args, options):
    """Tweet post url to twitter."""
    from birdy.twitter import UserClient
    client = UserClient(args.consumer_key, args.consumer_secret,
            args.access_token, args.access_token_secret)
    stanzas = get_stanzas_by_date(args.date)
    stanzas_count = len(stanzas)
    stanza_url = 'https://techshack.soasme.com/stanza-%s.html' % args.date
    if stanzas_count:
        message = '今天阅读了 %s 篇。#techshack %s' % (stanzas_count, stanza_url)
        response = client.api.statuses.update.post(status=message)
        if response.status_code != 200:
            sys.exit(response.content)

def prog_zen(args, options):
    """Print zen of this project."""
    print('Automate myself, and gain knowledge.')


def find_prog(prog):
    """Find prog function by parameter [prog]."""
    try:
        return globals()['prog_%s' % prog]
    except KeyError:
        raise Exception('Prog %s not found' % prog)


def main():
    """Main entry.

    Support multiple level prog.

        $ python techshack.py zen
        $ python techshack.py zen unknown -n
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('prog', help='program', nargs='+')
    args, unknown = parser.parse_known_args()
    prog_name = args.prog[0]
    prog = find_prog(prog_name)
    prog(args.prog[1:], unknown)


if __name__ == '__main__':
    main()
