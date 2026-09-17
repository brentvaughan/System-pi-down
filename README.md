# Equipment Downtime Tracker

A small Flask app for tracking when a piece of equipment goes down, who to
email to order the replacement part, and getting reminded throughout the
day about anything that's still down. Designed to run on a Raspberry Pi.

## What it does

- **Track status.** Each piece of equipment has an up/down status, with a
  full history of when it went down/came back up and why.
- **Order the part automatically.** Each piece of equipment can have a
  part name/number and a vendor email. Marking it "down" immediately
  emails that vendor (plus your own reminder address) asking for the part.
- **Remind you during the day.** A background job periodically emails you
  a summary of everything still down and how long it's been down, during
  configurable active hours (so you're not paged at 3am). It only sends
  when something is actually down.
- **Multiple ways to report status:** the web dashboard, a JSON API
  (`POST /api/equipment/<id>/status`), or a CLI script — whatever's
  convenient in the moment you notice a machine is down.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM` —
  your outgoing mail server. If you leave `SMTP_HOST` blank, emails are
  logged to the console instead of sent, so you can try the app out first.
- `REMINDER_EMAIL` — your own address(es), comma-separated. Gets the
  periodic "still down" reminders and a copy of every part-order email.
- `REMINDER_INTERVAL_MINUTES` and `REMINDER_ACTIVE_START_HOUR` /
  `REMINDER_ACTIVE_END_HOUR` — how often to remind you, and during what
  hours.

Run it:

```bash
python run.py
```

Then open `http://<pi-hostname>:5000/` from any device on your network.

## Using it

1. Add each piece of equipment once, with its part name/number and the
   vendor email that should receive the order request.
2. When something breaks, click "Mark down" (or use the CLI/API below).
   The vendor gets an email immediately.
3. When it's fixed, click "Mark up". You'll get an email noting how long
   it was down.
4. While anything is down, you'll get a reminder email every
   `REMINDER_INTERVAL_MINUTES` during active hours listing everything
   that's still out, so nothing gets forgotten by end of day.

### CLI

```bash
python report_status.py list
python report_status.py down "Table Saw" --note "blade snapped"
python report_status.py up "Table Saw" --note "replaced blade"
```

### API

```bash
curl -X POST http://localhost:5000/api/equipment/1/status \
  -H 'Content-Type: application/json' \
  -d '{"status": "down", "note": "blade snapped"}'
```

## Running it as a service on the Pi

Create `/etc/systemd/system/downtime-tracker.service`:

```ini
[Unit]
Description=Equipment Downtime Tracker
After=network.target

[Service]
WorkingDirectory=/home/pi/System-pi-down
ExecStart=/home/pi/System-pi-down/.venv/bin/python run.py
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl enable --now downtime-tracker
```

## Tests

```bash
pip install pytest
pytest
```
