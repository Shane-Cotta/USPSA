# ClassifierTracker

Minimal Django 5.x project to track USPSA classifier scores per user, compute divisions, and (optionally) collect PractiScore results.

## Setup
1. Create and activate a Python 3.12 virtualenv.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and adjust values. By default it points to the local Postgres container.
4. Start Postgres locally:
   ```bash
   docker-compose up -d db
   ```
5. Run migrations and create a superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Tests
Run the pytest suite:
```bash
pytest
```

## Collectors
Configure ClubSource and MatchSource in Django admin, then run:
```bash
python manage.py run_collectors
```
