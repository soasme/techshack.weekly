# -*- coding: utf-8 -*-

import os
from simplenote import Simplenote
import sqlite3
from time import sleep

simplenote = Simplenote(os.environ['SIMPLENOTE_USER'], os.environ['SIMPLENOTE_PASS'])

def fetchrows(conn):
    cursor = conn.cursor()
    cursor.execute("select * from stanza order by created desc")
    for row in cursor:
        yield row

def group_by_date(rows):
    prev = None
    batch = []
    for row in rows:
        uuid, dt, ref, thoughts, tags = row
        date = dt[0:10]

        if prev is None:
            prev = date

        if prev != date:
            yield batch
            batch = [row]
        else:
            batch.append(row)
        prev = date
    if batch:
        yield batch

def create_note(batch):
    output = []
    for row in batch:
        uuid, dt, ref, thoughts, tags = row
        date = dt[0:10]
        if date in ('2017-12-05', '2017-12-03'):
            return
        if not output:
            output.append('# Techshack %s' % date)
        output.append('')
        output.append('')
        output.append('---')
        output.append('')
        output.append('* uuid: %s' % uuid)
        output.append('* url: %s' % ref)
        output.append('* tags: %s' % tags)
        output.append('')
        output += thoughts.splitlines()
    return '\n'.join(output)

def sync_note(content):
    note = {
        'content': content,
        'tags': ['techshack'],
        'systemtags': ['markdown']
    }
    print(note)
    simplenote.add_note(note)

def make_public():
    notes, status = simplenote.get_note_list(since='2017-12-04', tags=['techshack'])
    for note in notes:
        if 'published' not in note:
            note['systemtags'].append('published')
            newnote, status = simplenote.update_note(note)
            print(newnote)
            sleep(1)

def main():
    make_public()

def import_notes():
    conn = sqlite3.connect('/tmp/data.db')
    data = fetchrows(conn)
    for batch in group_by_date(data):
        content = create_note(batch)
        if not content:
            continue
        sync_note(content)
        sleep(3)
    conn.close()

if __name__ == '__main__':
    main()
