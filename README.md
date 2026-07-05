# Meaco Stock Monitor

Watches a list of Meaco air conditioner/dehumidifier products on
[meaco.com](https://www.meaco.com) and emails you the moment one goes from
**out of stock → in stock**. Runs for free on GitHub Actions — no server to
maintain.

It only emails on the *transition* to in-stock, so you don't get spammed
every run while a product just sits in stock or stays sold out.

## How it works

1. A GitHub Actions workflow ([.github/workflows/monitor.yml](.github/workflows/monitor.yml))
   runs [meaco_stock_monitor.py](meaco_stock_monitor.py) on a schedule.
2. The script hits each product's Shopify `.js` endpoint (e.g.
   `https://www.meaco.com/products/<handle>.js`) and reads the `available`
   field.
3. It compares that against the last known state, cached in
   `meaco_stock_state.json` between runs (restored/saved via
   `actions/cache`).
4. Any product that flipped to in-stock gets included in one email, sent
   over SMTP.

## Setup (so it emails *you*)

This repo has no hardcoded email or credentials — everything is supplied via
GitHub Actions secrets, so anyone can fork/clone it and wire it to their own
inbox.

1. **Fork this repo** into your own GitHub account.
2. **Enable Actions on your fork.** GitHub disables scheduled workflows on
   forks by default. Go to the **Actions** tab on your fork — you'll see a
   banner saying workflows are disabled — click **"I understand my
   workflows, go ahead and enable them"**. Without this step, nothing will
   ever run, no matter how the secrets are set.
3. Go to **Settings → Secrets and variables → Actions** on your repo and add:

   | Secret | Example | Notes |
   |---|---|---|
   | `SMTP_HOST` | `smtp.gmail.com` | Gmail shown here; any SMTP+STARTTLS provider works |
   | `SMTP_PORT` | `587` | |
   | `SMTP_USER` | `you@gmail.com` | The account that sends the email |
   | `SMTP_PASS` | `xxxx xxxx xxxx xxxx` | A Gmail **App Password**, not your real password (requires 2FA enabled on the Google account) |
   | `ALERT_TO` | `you@gmail.com` | Where the alert is delivered — can differ from `SMTP_USER` |

   To create a Gmail App Password:
   1. Make sure [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification) is turned on for your Google account (App Passwords won't show up otherwise).
   2. Go directly to **[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)**.
   3. Enter a name like "Meaco Monitor" and click **Create**.
   4. Google shows a 16-character password (e.g. `abcd efgh ijkl mnop`) — copy it as-is (spaces are fine) and use it as `SMTP_PASS`. It's shown once and can't be viewed again.

4. Edit the `HANDLES` list at the top of
   [meaco_stock_monitor.py](meaco_stock_monitor.py) to the Shopify handles of
   the products you want to watch (the last part of the product URL on
   meaco.com), commit, and push to your fork.
5. That's it — once Actions is enabled and secrets are set, the workflow
   picks them up automatically on the next scheduled run. No further setup
   needed.

### Sending a one-off test email

Go to the **Actions** tab → **Meaco Stock Monitor** → **Run workflow**, set
`test_email` to `yes`, and run it. This sends a canned "TEST" email using
your configured secrets so you can confirm delivery without waiting for
real stock to change.

## ⏱️ About the schedule (important)

The workflow is configured with:

```yaml
schedule:
  - cron: "*/5 * * * *"   # every 5 minutes
```

**In practice, GitHub only runs it roughly every 30-45 minutes (sometimes
longer)**, not every 5. This isn't a bug in this repo — it's a documented
GitHub Actions limitation:

- Scheduled workflows are **not guaranteed** to run at the exact time
  requested.
- On the free tier, high-frequency cron schedules (anything under ~15-20
  min) get silently delayed and queued behind other scheduled jobs across
  GitHub's entire infrastructure, especially during peak load.
- GitHub explicitly recommends against very short intervals for this
  reason.

So treat `*/5 * * * *` as "as often as GitHub will allow, with 5 minutes as
a floor" rather than a guarantee. If you need tighter timing than GitHub
Actions can reliably give you, you'd need to run this on your own
always-on host/cron (e.g. a Raspberry Pi, VPS, or a paid CI runner) instead.

**Also note:** GitHub auto-disables scheduled workflows on any repo
(including forks) after **60 days with no commits/activity**. If your
monitor mysteriously stops emailing, check the Actions tab — you may just
need to re-enable it.

## Files

| File | Purpose |
|---|---|
| `meaco_stock_monitor.py` | The monitor + emailer |
| `.github/workflows/monitor.yml` | Schedules the script and injects secrets |
| `meaco_stock_state.json` | Auto-generated stock cache (not committed — gitignored) |

## Disclaimer

This is a personal-use polling script against publicly available product
JSON. Be a reasonable citizen: don't drop the interval below what's set
here, and don't run many parallel copies against the same site.
