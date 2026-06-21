# Dailyflow Workout Tracker

A personal, single-user Flask app to track workouts, body weight, water, meals, and progress — local-first with SQLite, no auth.

## Features
- **Dashboard** — daily quote, today's stats, live weigh-in countdown, and a routine-aware consistency heatmap (done / missed / rest / bonus).
- **Workout** — log exercises (sets/reps/weight) for any date; edit, complete, or delete. Add workout routine.
- **Water** — tap to add 500ml toward a 3L daily goal.
- **Meals** — one-tap logging from your saved meal templates, with calories + macros (protein/carbs/fat) vs. bodyweight-based targets.
- **Weight** — log/edit/delete entries with charts. Tracking.
- **Settings** — height, goal & activity (drives calorie/macro targets + BMI) and a configurable workout **routine** (alternating cycle or weekly split).

## Stack
Flask · SQLite (raw `sqlite3`) · Jinja2 templates + vanilla JS. No build step.

## Run
```bash
pip install -r requirements.txt
python app.py        # http://localhost:5000
```
The database is created and seeded automatically on first run.
