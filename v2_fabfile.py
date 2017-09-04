# -*- encoding: utf-8 -*-

import os
from fabric.api import run, env, cd
from fabric.operations import put

env.hosts = ['balance']
env.use_ssh_config = True
env.etc_path = '/etc/techshack.io'
env.data_path = '/data/techshack.io'
env.html_path = '/var/www/techshack.io/html'
env.home_path = '/var/www/techshack.io'
env.python_path = '/var/www/techshack.io/venv/bin/python'
env.pip_path = '/var/www/techshack.io/venv/bin/pip'
env.runner_path = '/var/www/techshack.io/techshack.py'
env.requirements = 'slackbot mistune dropbox birdy jinja2'

def kill_pids(commands):
    for pid in run(pids).splitlines():
        if pid:
            run("kill -9 %s" % pid)

def prepare_folders():
    run('mkdir -p {etc_path} {data_path} {html_path}/static'.format(env))

def upload_files():
    put('./html/static/tech-shack.png', '{html_path}/static'.format(env))
    put('./.env', '{etc_path}/env'.format(env))
    put('./techshack.py', '{runner_path}'.format(env), mode=755)

def stop_service():
    kill_pids("ps aux | grep techshack.py | grep -v grep | awk '{print $2}'")

def install_dependencies():
    run('{pip_path} install -q {requirements}'.format(env))

def start_service():
    run('(nohup {python_path} {runner_path} slackbot &) && sleep 1'.format(env))

def set_cron(tag, commands):
    return 'crontab -l | grep -v %(tag)s | {cat; %(commands)s } | crontab -' % {
            'tag': tag, 'commands': commands}

def start_periodical_tasks():
    run(set_cron('techshack', (
        "echo '*/10 * * * * "
        "{python_path} {runner_path} publish && "
        "curl -fsS --retry 3 "
        "https://hchk.io/9c427328-f3f0-4265-8d20-b142f321a0fb "
        "> /dev/null';"

        "echo '*/10 * * * * "
        "{python_path} {runner_path} backup && "
        "curl -fsS --retry 3 "
        "https://hchk.io/f5a2eb4b-611d-40a8-bfe7-cdc1b2617f8d "
        "> /dev/null';"
    ).format(env)))

def deploy():
    prepare_folders()
    upload_files()
    stop_service()
    install_dependencies()
    start_service()
    start_periodical_tasks()
