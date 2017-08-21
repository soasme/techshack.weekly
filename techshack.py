#/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse


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
