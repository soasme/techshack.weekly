#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse
import csv
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from uuid import uuid4


def prepare_database(conn):
    """Create tables."""
    cursor = conn.cursor()
    cursor.execute("create table if not exists stanza (id text primary key, created text, ref text, thoughts text, tags text)")
    conn.commit()


@contextmanager
def open_database():
    """
    * ENV required: `STANZA_FILE_PATH`.

    with open_database() as conn:
        do_something(conn)
    """
    path = os.environ.get('STANZA_FILE_PATH')
    conn = sqlite3.connect(path)
    prepare_database(conn)
    try:
        yield conn
    finally:
        conn.close()


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


def prog_slackbot(args, options):
    """

    * ENV required: `SLACKBOT_API_TOKEN`.

    """
    from slackbot.bot import Bot
    from slackbot.bot import respond_to
    import re
    import json

    @respond_to('ping', re.IGNORECASE)
    def respond_to_github(message):
        message.reply('pong')

    @respond_to('show stanza (.*)', re.IGNORECASE)
    def show_stanza(message, uuid):
        with open_database() as conn:
            stanza = get_stanza(conn, uuid)
            if not stanza:
                message.reply('stanza %s not found' % uuid)
            else:
                message.reply(format_stanza(stanza))

    @respond_to('save stanza (.*)', re.IGNORECASE)
    def save_stanza_to_dat(message, url):
        with open_database() as conn:
            uuid = create_stanza(conn, url)
            start_stanza_session(uuid)
            message.reply('Start editing %s' % uuid)

    @respond_to('edit stanza (.*)', re.IGNORECASE)
    def edit_stanza(message, uuid):
        with open_database() as conn:
            if get_stanza(conn, uuid):
                start_stanza_session(uuid)
                message.reply('Start editing %s' % uuid)
            else:
                message.reply('Stanza %s not found' % uuid)

    @respond_to('done stanza')
    def stop_editing_stanza(message):
        with open_database() as conn:
            uuid = get_stanza_session()
            if uuid:
                destroy_stanza_session()
                message.reply('Quit editing %s' % uuid)
                message.reply(format_stanza(get_stanza(conn, uuid)))
            else:
                message.reply('No session found.')

    @respond_to('thoughts (.*)')
    def set_stanza_thoughts_to_dat(message, thoughts):
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

    @respond_to('tags (.*)')
    def set_stanza_tags_to_dat(message, tags):
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


    bot = Bot()
    bot.run()


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
