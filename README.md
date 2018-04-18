Install dependencies:

```
$ pipenv install
```

---

## Daily

Sync data.

```
$ make db
```

Sync growth stats.

```
$ make growth_stats
```

Pub tweets

```
$ make tweets
```

## Weekly

```
$ export ISSUE=0006 # replace it to new issue.
```
Send to telegram

```
$ make telegram_message > /tmp/$ISSUE.md
$ pipenv run ./admin.py push_to_telegram_channel /tmp/$ISSUE.md
$ pipenv run ./admin.py push_to_telegram_channel /tmp/$ISSUE.md --release
```

Send to mailchimp

```
$ make mailchimp_message > /tmp/$ISSUE.md
$ make mailchimp
```

