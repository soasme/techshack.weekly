Install dependencies:

```
$ pipenv install
```

---

Sync data.

```
$ make db
```

```
$ make ISSUE=0006 telegram_message > /tmp/0006.md
$ pipenv run ./admin.py push_to_telegram_channel /tmp/0006.md
$ pipenv run ./admin.py push_to_telegram_channel /tmp/0006.md --release
```

https://domchristie.github.io/turndown/
