# -*- encoding: utf-8 -*-

import os
from fabric.api import run
from fabric.operations import put

def deploy():
    slack_api_token = os.environ['SLACK_API_TOKEN']
    run('mkdir -p /data/techshack.io /var/www/techshack.io/html/static')
    put('./html/static/tech-shack.png', '/var/www/techshack.io/html/static/')
    put('./techshack.py', '/var/www/techshack.io/techshack.py', mode=0755)
    run("ps aux | grep techshack.py | awk '{print $1}' | xargs kill -9")
    run('env SLACK_API_TOKEN=%s STANZA_FILE_PATH=/data/techshack.io/stanza.dat '
        'nohup /var/www/techshack.io/venv/bin/python '
        '/var/www/techshack.io/techshack.py '
        'slackbot > /var/www/techshack.io/nohup.out' % slack_api_token)
    run("crontab -l | grep -v techshack | { cat; echo '0 * * * * env "
        "STANZA_FILE_PATH=/data/techshack.io/stanza.dat "
        "/var/www/techshack.io/venv/bin/python "
        "/var/www/techshack.io/techshack.py publish "
        "--dest /var/www/techshack.io/html --before-days 2' } | crontab -")
    run("echo 'server { listen 80; server_name tools.soasme.com; location / { "
        "root /var/www/techshack.io/html }}' > "
        "/etc/nginx/sites-enabled/tools_soasme_com_80.conf")
    run("service nginx reload")
