#/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse
import csv
import os
from datetime import datetime
from io import StringIO
from uuid import uuid4


def save_stanza(uuid, ref, thoughts, tags):
    """Save a piece of stanza.

    * ENV required: `STANZA_FILE_PATH`.
    """
    tags = tags.replace(',', '|')
    with open(os.environ.get('STANZA_FILE_PATH'), 'a') as f:
        writer = csv.writer(f)
        row = [
            str(uuid),
            datetime.utcnow().isoformat() + '+0000',
            ref,
            thoughts,
            tags.replace(',', '|'),
        ]
        writer.writerow(row)


def get_stanza(uuid):
    with open(os.environ.get('STANZA_FILE_PATH', 'w')) as f:
        reader = csv.reader(f)
        stanza = None
        for row in reader:
            if row[0] == uuid:
                stanza = row
        return stanza


def prog_slackbot(args, options):
    """

    * ENV required: `SLACKBOT_API_TOKEN`.

    """
    from slackbot.bot import Bot
    from slackbot.bot import respond_to
    import re
    import json

    @respond_to('echo (.*)', re.IGNORECASE)
    def respond_to_github(message, something):
        message.reply(something)

    @respond_to('show stanza (.*)', re.IGNORECASE)
    def show_stanza(message, uuid):
        stanza = get_stanza(uuid)
        if not stanza:
            message.reply('stanza %s not found' % uuid)
        else:
            message.reply("""
uuid: %s
created: %s
ref: %s
thoughts: %s
tags: %s
            """ % tuple(stanza))


    @respond_to('save stanza (.*)', re.IGNORECASE)
    def save_stanza_to_dat(message, dat):
        reader = csv.reader(StringIO(dat), delimiter=',')
        row = next(reader)
        if len(row) == 3:
            uuid = uuid4()
            ref, thoughts, tags = row
            save_stanza(uuid, ref, thoughts, tags)
            show_stanza(message, str(uuid))
        elif len(row) == 4:
            uuid, ref, thoughts, tags = row
            save_stanza(uuid, ref, thoughts, tags)
            show_stanza(message, str(uuid))


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
