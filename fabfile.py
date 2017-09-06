# -*- encoding: utf-8 -*-

import os
from fabric.api import run, env, cd
from fabric.operations import put
import techshack

env.hosts = ['balance']
env.use_ssh_config = True
slackbot_api_token = techshack.config('SLACKBOT_API_TOKEN')
dropbox_api_token = techshack.config('DROPBOX_API_TOKEN')
stanza_file_path = techshack.config('STANZA_FILE_PATH')

def deploy():
    run('mkdir -p /data/techshack.io /var/www/techshack.io/html /etc/techshack.io')
    put('./.env', '/etc/techshack.io/env')
    put('./techshack.py', '/var/www/techshack.io/techshack.py', mode=755)
    for pid in run("ps aux | grep techshack.py | grep -v grep | awk '{print $2}'").splitlines():
        if pid:
            run("kill -9 %s" % pid)
    with cd('/var/www/techshack.io'):
        run('/var/www/techshack.io/venv/bin/pip install -q slackbot mistune dropbox birdy')
        run('(nohup /var/www/techshack.io/venv/bin/python '
            '/var/www/techshack.io/techshack.py slackbot &) && sleep 1')
        run("crontab -l | grep -v techshack "
            "| { cat; "

            "echo '*/10 * * * * "
            "/var/www/techshack.io/venv/bin/python "
            "/var/www/techshack.io/techshack.py publish "
            "--dest /var/www/techshack.io/html --before-days 2 && "
            "curl -fsS --retry 3 "
            "https://hchk.io/9c427328-f3f0-4265-8d20-b142f321a0fb "
            "> /dev/null';"

            "echo '*/10 * * * * "
            "/var/www/techshack.io/venv/bin/python "
            "/var/www/techshack.io/techshack.py backup "
            "--src /data/techshack.io/stanza.dat "
            "--dest /backups/stanza.dat "
            "--token %(dropbox_api_token)s && "
            "curl -fsS --retry 3 "
            "https://hchk.io/f5a2eb4b-611d-40a8-bfe7-cdc1b2617f8d "
            "> /dev/null';"

            "echo '*/10 * * * * "
            "/var/www/techshack.io/venv/bin/python "
            "/var/www/techshack.io/techshack.py tweet ';"

            "} | crontab -" % dict(
                dropbox_api_token=dropbox_api_token
            ))
        run("rm -f /var/www/techshack.io/html/*.html && "
            "/var/www/techshack.io/venv/bin/python "
            "/var/www/techshack.io/techshack.py publish "
            "--dest /var/www/techshack.io/html --before-days 100")
