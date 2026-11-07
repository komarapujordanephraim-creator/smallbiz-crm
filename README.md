# SmallBiz CRM

A small, self-hostable CRM for a single business or freelancer: contacts, companies, a deal pipeline, activity notes and a dashboard. Built with Django 5 and SQLite. It is a portfolio project that shows how I structure a business web app, not a replacement for a full CRM.

## What it does

- **Contacts and companies** with search (name, email, company) and CSV export.
- **Deal pipeline** with five stages: Lead, Qualified, Proposal, Won, Lost. A board view lets you move a deal between stages; won and lost deals get a close date automatically, and reopening a deal clears it.
- **Activity log** per contact (note, call, email, meeting), optionally linked to a deal.
- **Dashboard**: open pipeline value, value won this month, win rate (won divided by won plus lost), and value per stage.
- **Accounts**: every record belongs to the user who created it. Users only ever see their own data.

## Design decisions worth reading

- **Data isolation is enforced in one place.** Every model uses a queryset method `for_user()`. All views start from it, so another user's record returns 404 instead of leaking. Forms also limit their dropdowns to the user's own records, so you cannot attach a deal to someone else's contact by posting a crafted ID.
- **State changes need POST.** Moving a deal's stage is a POST with CSRF protection; a GET returns 405. Unknown stage values are ignored.
- **CSV export is safe to open in Excel.** Cells starting with `=`, `+`, `-` or `@` are prefixed with an apostrophe to stop formula injection.
- **No secrets in the repo.** `SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS` come from environment variables, with development defaults only.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # optional: demo user demo / demo12345 and fictional sample data
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in. To create your own account: `python manage.py createsuperuser`.

Run the tests (17 tests covering access control, stage logic, dashboard numbers, search and export):

```bash
python manage.py test
```

## Limits (what it does not do)

- Single database file (SQLite), no email sync, no reminders, no file attachments, no teams or shared records, no API.
- The demo login `demo / demo12345` is for local use only. Do not deploy with `seed_demo`.
- For production set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` and `DJANGO_ALLOWED_HOSTS`, serve static files properly and use HTTPS. I have not load-tested it.
- All sample names and companies are fictional.

## Tech

Python 3, Django 5.2, SQLite, plain HTML and CSS (no JavaScript framework).

## License

MIT. Built by Komarapu Jordan Ephraim.
