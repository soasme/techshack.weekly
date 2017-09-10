#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import re
import sys
import argparse
import csv
import os
import sqlite3
from contextlib import contextmanager
from functools import partial
from configparser import ConfigParser
from datetime import datetime, timezone
from io import StringIO
from uuid import uuid4

import mistune
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError as DropboxApiError, AuthError as DropboxAuthError

ROW_TEMPLATE = """<article class="post" id="%(uuid)s">
    <div class="post-content"><p>%(thoughts)s</p></div>
    <div class="post-permalink">
        <a class="btn btn-default read-original" href="%(ref_url)s" onclick="ga('send', 'event', 'Stanza', 'stanza %(date)s %(uuid)s', 'read-origin')">查看原文</a>
    </div>
    <footer class="post-footer clearfix">
        <div class="pull-left tag-list">%(tags)s</div>
    </footer>
</article>"""

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')) as f:
    SITE_TEMPLATE = f.read()

DEFAULT_CONFIGS = ['/etc/techshack.io/env', './.env']

config_parser = ConfigParser()
config_parser.read(next(f for f in DEFAULT_CONFIGS if os.path.exists(f)))
config = partial(config_parser.get, 'techshackd')

class MarkdownRenderer(mistune.Renderer):

    def codespan(self, text):
        return '<code>%s</code>' % mistune.escape(text.rstrip(), smart_amp=True)

def markdown(text):
    return mistune.Markdown(renderer=MarkdownRenderer())(text)

def prepare_database(conn):
    """Create tables."""
    cursor = conn.cursor()
    cursor.execute("create table if not exists stanza (id text primary key, created text, ref text, thoughts text, tags text)")
    conn.commit()


@contextmanager
def open_database():
    path = config('STANZA_FILE_PATH')
    conn = sqlite3.connect(path)
    prepare_database(conn)
    try:
        yield conn
    finally:
        conn.close()


def get_stats(conn):
    cursor = conn.cursor()
    cursor.execute("""select count(distinct substr(created, 0, 11)) as days,
            count(1) as cnt, sum(length(thoughts)) as text_length from stanza""")
    return dict(zip('days stanza_count txt_count'.split(), list(cursor.fetchone())))


def get_stanzas(conn):
    cursor = conn.cursor()
    cursor.execute("select * from stanza order by created desc")
    seg = []
    for stanza in cursor:
        if not seg or seg[-1][1][:10] == stanza[1][:10]:
            seg.append(stanza)
        else:
            yield seg[-1][1][:10], seg
            seg = [stanza]
    if seg:
        yield seg[-1][1][:10], seg


def get_stanza(conn, uuid):
    cursor = conn.cursor()
    cursor.execute("select * from stanza where id=?", (uuid, ))
    return cursor.fetchone()


def create_stanza(conn, ref):
    cursor = conn.cursor()
    uuid = str(uuid4())
    created = datetime.utcnow().isoformat() + '+0000'
    cursor.execute("insert into stanza(id,created,ref) values(?,?,?)", (uuid, created, ref, ))
    conn.commit()
    return uuid


def set_stanza_thoughts(conn, uuid, thoughts):
    cursor = conn.cursor()
    cursor.execute("update stanza set thoughts=? where id=?", (thoughts, uuid, ))
    conn.commit()


def set_stanza_tags(conn, uuid, tags):
    cursor = conn.cursor()
    tags = tags.replace(',', '|')
    cursor.execute("update stanza set tags=? where id=?", (tags, uuid, ))
    conn.commit()


def format_stanza(stanza):
    return """uuid: %s
created: %s
ref: %s
thoughts: %s
tags: %s""" % tuple(stanza)

def format_pub_stanza(stanza, tag):
    uuid, created, ref, thoughts, tags = stanza
    try:
        thoughts = thoughts[:thoughts.index('。')]
    except ValueError:
        thoughts = thoughts[:125]
    thoughts = len(thoughts) > 125 and thoughts[:125] + '... ' or thoughts + ' '
    thoughts = thoughts + tag
    stanza_url = 'https://techshack.soasme.com/stanza-%s.html#%s' % (created[:10], uuid, )
    return '%s%s' % (thoughts, stanza_url)

def parse_import_content(content):
    lines = content.strip().splitlines()
    url =lines[0].replace('import stanza ', '').strip()
    tags = lines[-1].strip()
    thoughts = '\n'.join(lines[1:-1])
    return url, thoughts, tags

def get_douban_token():
    if os.path.exists('/tmp/techshack.io.douban.session'):
        with open('/tmp/techshack.io.douban.session') as f:
            return f.read()

def save_douban_token(token):
    with open('/tmp/techshack.io.douban.session', 'w') as f:
        f.write(token)

def auth_douban_token(code):
    client = get_douban_raw_client()
    client.auth_with_code(code)
    save_douban_token(client.token_code)
    return client

def get_douban_raw_client():
    from douban_client import DoubanClient
    return DoubanClient(config('DOUBAN_API_KEY'), config('DOUBAN_API_SECRET'),
            'https://' + config('DOMAIN'), config('DOUBAN_API_SCOPE'))

def get_douban_client():
    client = get_douban_raw_client()
    token = get_douban_token()
    if token: client.auth_with_token(token)
    return client

def pub_douban(message):
    client = get_douban_client()
    res = client.miniblog.new(message)
    return 'https://www.douban.com/people/%s/status/%s/' % (
            config('DOUBAN_USERNAME'), res['id'])

def pub_tweet(message):
    from birdy.twitter import UserClient
    client = UserClient(config('TWITTER_API_CONSUMER_KEY'),
            config('TWITTER_API_CONSUMER_SECRET'),
            config('TWITTER_API_ACCESS_TOKEN'),
            config('TWITTER_API_ACCESS_SECRET'))
    user = config('TWITTER_USERNAME')
    res = client.api.statuses.update.post(status=message)
    return 'https://twitter.com/%s/status/%s' % (user, res.data['id'])

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


def bot_pub_designated_stanza(message, sns, uuid):
    with open_database() as conn:
        stanza = get_stanza(conn, uuid)
        if not stanza:
            message.reply('no stanza found. pub to %s failed.' % sns)
        else:
            pub = globals()['pub_' + sns]
            tag = '#techshack# ' if sns == 'douban' else '#techshack '
            url = pub(format_pub_stanza(stanza, tag))
            message.reply(url)

def bot_pub_stanza(message, sns):
    session = get_stanza_session()
    if not session:
        message.reply('no session found. pub to %s failed.' % sns)
    else:
        bot_pub_designated_stanza(message, sns, session)

def bot_need_auth_douban(message):
    message.reply(get_douban_raw_client().authorize_url +
            ' type `auth douban xxxx` after authorization completed')

def bot_auth_douban(message, code):
    client = auth_douban_token(code)
    message.reply("you're %s, right?" % client.user.me['name'])

def bot_build_site(message):
    prog_publish()
    message.reply('Done')

def bot_respond_ping(message):
    message.reply('pong')

def bot_show_stanza(message, uuid):
    with open_database() as conn:
        stanza = get_stanza(conn, uuid)
        if not stanza:
            message.reply('stanza %s not found' % uuid)
        else:
            message.reply(format_stanza(stanza))

def bot_import_stanza(message, content):
    with open_database() as conn:
        url, thoughts, tags = parse_import_content(content)
        uuid = create_stanza(conn, url)
        set_stanza_thoughts(conn, uuid, thoughts)
        set_stanza_tags(conn, uuid, tags)

def bot_save_stanza(message, url):
    with open_database() as conn:
        uuid = create_stanza(conn, url)
        start_stanza_session(uuid)
        message.reply('Start editing %s' % uuid)

def bot_edit_stanza(message, uuid):
    with open_database() as conn:
        if get_stanza(conn, uuid):
            start_stanza_session(uuid)
            message.reply('Start editing %s' % uuid)
        else:
            message.reply('Stanza %s not found' % uuid)

def bot_quit_stanza(message):
    with open_database() as conn:
        uuid = get_stanza_session()
        if uuid:
            destroy_stanza_session()
            message.reply('Quit editing %s' % uuid)
            message.reply(format_stanza(get_stanza(conn, uuid)))
        else:
            message.reply('No session found.')

def bot_set_stanza_thoughts(message, thoughts):
    with open_database() as conn:
        uuid = get_stanza_session()
        if uuid:
            stanza = get_stanza(conn, uuid)
            if stanza:
                set_stanza_thoughts(conn, uuid, thoughts)
                message.reply('Done')
            else:
                destroy_stanza_session()
                message.reply('Stanza %s not found' % uuid)
        else:
            message.reply('No session found.')

def bot_set_stanza_tags(message, tags):
    with open_database() as conn:
        uuid = get_stanza_session()
        if uuid:
            stanza = get_stanza(conn, uuid)
            if stanza:
                set_stanza_tags(conn, uuid, tags)
                message.reply('Done')
            else:
                destroy_stanza_session()
                message.reply('Stanza %s not found' % uuid)
        else:
            message.reply('No session found.')

def bot_restart_himself(message):
    pid = os.fork()
    if pid == 0:
        os.system('curl https://raw.githubusercontent.com/soasme/techshack.io/master/techshack.py > %s' % (config('HOME_PATH') + '/techshack.py'))
        os.system('nohup %s %s slackbot > %s &' % (
            config('BIN_PATH') + '/python',
            config('HOME_PATH') + '/techshack.py',
            config('HOME_PATH') + '/service.log'
            ))
    os.system('kill -9 %s' % os.getpid())


def load_bot_command():
    from slackbot.bot import respond_to
    respond_to('pub (\w+) ([0-9a-z\-]+)$', re.IGNORECASE)(bot_pub_designated_stanza)
    respond_to('pub (\w+)$', re.IGNORECASE)(bot_pub_stanza)
    respond_to('need auth douban', re.IGNORECASE)(bot_need_auth_douban)
    respond_to('auth douban (.*)', re.IGNORECASE)(bot_auth_douban)
    respond_to('build site', re.IGNORECASE)(bot_build_site)
    respond_to('ping', re.IGNORECASE)(bot_respond_ping)
    respond_to('show stanza (.*)', re.IGNORECASE)(bot_show_stanza)
    respond_to('save stanza (.*)', re.IGNORECASE)(bot_save_stanza)
    respond_to('edit stanza (.*)', re.IGNORECASE)(bot_edit_stanza)
    respond_to('done stanza')(bot_quit_stanza)
    respond_to('import stanza (.*)', re.DOTALL | re.IGNORECASE)(bot_import_stanza)
    respond_to('thoughts (.*)', re.DOTALL | re.IGNORECASE)(bot_set_stanza_thoughts)
    respond_to('tags (.*)')(bot_set_stanza_tags)
    respond_to('restart yourself')(bot_restart_himself)

def prog_slackbot(args, options):
    os.environ['SLACKBOT_API_TOKEN'] = config('SLACKBOT_API_TOKEN')
    from slackbot.bot import Bot
    load_bot_command()
    Bot().run()

def prog_publish(args=None, options=None):
    with open_database() as conn:
        index, latest_date = 1, None
        for date, stanzas in get_stanzas(conn):
            latest_date = latest_date or date
            widgets = []
            raw_tags = set()
            for stanza in stanzas:
                uuid, created, ref, thoughts, tags = stanza
                if not thoughts or not tags:
                    continue
                ref_url = ref[1:-1] if ref.startswith('<') and ref.endswith('>') else '#'
                thoughts = re.sub(r'<(.*)>', r'<a href="\1">\1</a>', thoughts)
                raw_tags = raw_tags | set([tag for tag in tags.split('|') if tag])
                tags = ''.join(['<span class="label label-default">%s</span>' % tag for tag in tags.split('|') if tag])
                html_thoughts = markdown(thoughts)
                widget = ROW_TEMPLATE % dict(uuid=uuid, thoughts=html_thoughts, ref_url=ref_url, tags=tags, date=date)
                widgets.append(widget)

            slogan = '技术阅读+一些思考'
            context = dict(title='Tech Shack',
                jumbotron_text='%s<br>%s' % (slogan, date),
                author='Ju Lin <soasme@gmail.com>',
                date=date,
                latest_date=latest_date,
                program_name="Tech Shack",
                description='%s, 本期关键词: %s' % (slogan, ', '.join(raw_tags)),
                posts=''.join(widgets),
            )
            context.update({'stats_%s' % k: v for k, v in get_stats(conn).items()})
            page = SITE_TEMPLATE % context
            page = ''.join(page.splitlines())

            with open(os.path.join(config('HTML_PATH'), 'stanza-%s.html' % date), 'w') as f:
                f.write(page)

            if index == 1:
                with open(os.path.join(config('HTML_PATH'), 'index.html'), 'w') as f:
                    f.write(page)

            index += 1


def prog_backup(args, options):
    with open(config('STANZA_FILE_PATH'), 'rb') as f:
        dbx = dropbox.Dropbox(config('DROPBOX_API_TOKEN'))
        dbx.users_get_current_account()
        dbx.files_upload(f.read(),
                config('REMOTE_BACKUP_STANZA_FILE_PATH'), mode=WriteMode('overwrite'))


def prog_zen(args, options):
    print('Automate myself, and gain knowledge.')


def find_prog(prog):
    try:
        return globals()['prog_%s' % prog]
    except KeyError:
        raise Exception('Prog %s not found' % prog)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('prog', help='program', nargs='+')
    args, unknown = parser.parse_known_args()
    prog_name = args.prog[0]
    prog = find_prog(prog_name)
    prog(args.prog[1:], unknown)


if __name__ == '__main__':
    main()
