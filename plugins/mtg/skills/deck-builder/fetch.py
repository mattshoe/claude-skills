#!/usr/bin/env python3
"""Save a decklist as a Fetch list in the user's app, the same on web and Android.

Usage: fetch.py "TITLE" list.txt
Needs ~/.mtg-api.env loaded. Reads the account's saved lists from /fetch-lists with the admin token and the owner's id,
puts the new one first, replacing any list with the same title, and writes the set back. It's saved without a result,
so the app shows the list and the user taps Find to see where every card is.
"""
import datetime, json, os, sys, urllib.request

api, owner = os.environ['MTG_API_URL'], int(os.environ['MTG_OWNER_ID'])
title, text = sys.argv[1].strip(), open(sys.argv[2]).read().strip()


def call(path, body=None, token=None):
    h = {'Content-Type': 'application/json', 'User-Agent': 'mtg-deck-builder/1.0'}
    if token:
        h['authorization'] = 'Bearer ' + token
    data = json.dumps(body).encode() if body is not None else None
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(api + path, data, h), timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f'{path} failed, {e.code}: {e.read().decode()[:300]}')


token = call('/admin', {'password': os.environ['MTG_ADMIN_PASSWORD']})['token']
lists = call(f'/fetch-lists?user={owner}', token=token)['lists']
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
old = next((l for l in lists if l.get('title') == title), None)
entry = {'id': old['id'] if old else f'{now}-{len(lists)}', 'title': title, 'at': now, 'list': text,
         'result': None, 'ticked': [], 'tickedMissing': []}
call('/fetch-lists', {'user': owner, 'lists': [entry] + [l for l in lists if l.get('title') != title]}, token)
after = [l['title'] for l in call(f'/fetch-lists?user={owner}', token=token)['lists']]
if title not in after:
    sys.exit('the list did not save')
print(f'Saved "{title}" as a Fetch list, {len(text.splitlines())} lines. The account now has {len(after)} saved lists.')
