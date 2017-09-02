# -*- encoding: utf-8 -*-

import os
from fabric.api import run, env, cd
from fabric.operations import put

env.hosts = ['wkss-lb01']
env.use_ssh_config = True

def deploy():
    slackbot_api_token = os.environ['SLACKBOT_API_TOKEN']
    run('mkdir -p /data/techshack.io /var/www/techshack.io/html/static')
    put('./html/static/tech-shack.png', '/var/www/techshack.io/html/static/')
    put('./techshack.py', '/var/www/techshack.io/techshack.py', mode=755)
    for pid in run("ps aux | grep techshack.py | grep -v grep | awk '{print $2}'").splitlines():
        if pid:
            run("kill -9 %s" % pid)
    with cd('/var/www/techshack.io'):
        run('/var/www/techshack.io/venv/bin/pip install -q slackbot mistune')
        run('(env SLACKBOT_API_TOKEN=%s STANZA_FILE_PATH=/data/techshack.io/stanza.dat '
            'nohup /var/www/techshack.io/venv/bin/python '
            '/var/www/techshack.io/techshack.py slackbot &) && sleep 1' % slackbot_api_token)
        run("crontab -l | grep -v techshack | { cat; echo '*/10 * * * * env "
            "STANZA_FILE_PATH=/data/techshack.io/stanza.dat "
            "/var/www/techshack.io/venv/bin/python "
            "/var/www/techshack.io/techshack.py publish "
            "--dest /var/www/techshack.io/html --before-days 2'; } | crontab -")
        run("rm -f /var/www/techshack.io/html/*.html && "
            "env STANZA_FILE_PATH=/data/techshack.io/stanza.dat "
            "/var/www/techshack.io/venv/bin/python "
            "/var/www/techshack.io/techshack.py publish "
            "--dest /var/www/techshack.io/html --before-days 100")
        run("echo 'server { listen 80; server_name techshack.soasme.com; location / { "
            "root /var/www/techshack.io/html }}' > "
            "/etc/nginx/sites-enabled/techshack_soasme_com_80.conf")
        run("service nginx reload")
