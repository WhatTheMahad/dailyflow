from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import date, datetime, timedelta
from database import (
    init_db, add_exercise, get_exercises, delete_exercise,
    get_workout, get_or_create_workout, update_workout_weight, clear_workout_weight, add_workout_exercise,
    get_workout_exercises, toggle_exercise_completion, update_workout_exercise, delete_workout_exercise,
    get_water, get_or_create_water, update_water, increment_water,
    add_meal, get_meals, delete_meal,
    get_meal_templates, add_meal_template, delete_meal_template, add_meal_from_template,
    get_workout_history, get_exercise_progress, get_logged_workout_dates,
    get_detailed_workout_history, get_latest_weight,
    get_settings, update_settings, update_routine
)
import nutrition
import routine as routine_lib

app = Flask(__name__)


def resolve_date():
    """The date the page should operate on: ?date=/form date if valid, else today.
    Future dates are clamped to today."""
    raw = request.values.get('date')
    today = date.today()
    if raw:
        try:
            d = date.fromisoformat(raw)
            if d > today:
                d = today
            return d.isoformat()
        except ValueError:
            pass
    return today.isoformat()


def date_nav(day):
    """Navigation context for the date picker shown on date-aware pages."""
    d = date.fromisoformat(day)
    today = date.today()
    return {
        'date': day,
        'label': d.strftime('%a, %b %d, %Y'),
        'prev': (d - timedelta(days=1)).isoformat(),
        'next': (d + timedelta(days=1)).isoformat(),
        'today': today.isoformat(),
        'is_today': d == today,
    }


def current_weight_kg():
    """Latest logged body weight, or None."""
    latest = get_latest_weight()
    return latest['body_weight'] if latest else None


def current_targets():
    """Bodyweight-driven daily macro targets using current weight + settings."""
    settings = get_settings()
    weight = current_weight_kg()
    return nutrition.compute_targets(weight, settings['goal'], settings['activity'])


def routine_context():
    """Routine info for templates + the heatmap JS (mode/pattern/start/name)."""
    s = get_settings()
    return {
        'mode': s['routine_mode'] or 'cycle',
        'pattern': s['routine_pattern'] or 'WR',
        'start': s['routine_start'] or '2026-01-01',
        'name': s['routine_name'] or 'Routine',
        'description': routine_lib.describe(s['routine_mode'], s['routine_pattern'] or 'WR'),
    }


def is_today_workout():
    r = routine_context()
    return routine_lib.is_workout_day(
        date.today(), r['mode'], r['pattern'], date.fromisoformat(r['start']))

# --- Configuration ---
WATER_TARGET_ML = 3000          # daily water goal
WATER_SERVING_ML = 500          # one click = 500ml
WATER_TARGET_SERVINGS = WATER_TARGET_ML // WATER_SERVING_ML  # = 6
WEIGHT_CHECK_INTERVAL_DAYS = 7  # remind to weigh in every 7 days

# Motivational quotes — one is shown per day, rotating by day-of-year.
QUOTES = [
    ("The body achieves what the mind believes.", "Napoleon Hill"),
    ("Discipline is doing it even when you don't feel like it.", "Unknown"),
    ("The pain you feel today is the strength you feel tomorrow.", "Arnold Schwarzenegger"),
    ("Don't count the days, make the days count.", "Muhammad Ali"),
    ("The only bad workout is the one that didn't happen.", "Unknown"),
    ("Success starts with self-discipline.", "Unknown"),
    ("Take care of your body. It's the only place you have to live.", "Jim Rohn"),
    ("Strength does not come from winning. Struggles develop your strength.", "Arnold Schwarzenegger"),
    ("You don't have to be extreme, just consistent.", "Unknown"),
    ("Sweat is just fat crying.", "Unknown"),
    ("A one-hour workout is 4% of your day. No excuses.", "Unknown"),
    ("The hardest lift of all is lifting your butt off the couch.", "Unknown"),
    ("Push yourself because no one else is going to do it for you.", "Unknown"),
    ("Your only limit is you.", "Unknown"),
    ("Wake up with determination, go to bed with satisfaction.", "Unknown"),
    ("Good things come to those who sweat.", "Unknown"),
    ("Fall in love with taking care of yourself.", "Unknown"),
    ("The difference between try and triumph is a little 'umph'.", "Unknown"),
    ("Train insane or remain the same.", "Unknown"),
    ("Results happen over time, not overnight. Work hard, stay consistent.", "Unknown"),
    ("Be stronger than your excuses.", "Unknown"),
    ("Energy and persistence conquer all things.", "Benjamin Franklin"),
    ("Motivation gets you started. Habit keeps you going.", "Jim Ryun"),
    ("It never gets easier, you just get stronger.", "Unknown"),
    ("Slow progress is still progress.", "Unknown"),
    ("Don't wish for it, work for it.", "Unknown"),
    ("Today's actions are tomorrow's results.", "Unknown"),
    ("Champions train, losers complain.", "Unknown"),
    ("Make yourself proud.", "Unknown"),
    ("One day or day one. You decide.", "Unknown"),
    ("The gym is not the only place to grow. Grow every day.", "Unknown"),
]


def quote_of_the_day():
    """Deterministic quote that changes once every 24 hours."""
    day_index = date.today().timetuple().tm_yday  # 1..366
    text, author = QUOTES[day_index % len(QUOTES)]
    return {'text': text, 'author': author}


@app.route('/')
def index():
    today = date.today().isoformat()
    workout = get_or_create_workout(today)
    workout_exercises = get_workout_exercises(workout['id'])
    workout_dates = get_logged_workout_dates(365)

    # Meals summary for today
    meals = get_meals(today)
    total_calories = sum(m['calories'] or 0 for m in meals)
    total_protein = sum(m['protein'] or 0 for m in meals)
    total_carbs = sum(m['carbs'] or 0 for m in meals)
    total_fat = sum(m['fat'] or 0 for m in meals)

    # Water summary for today
    water = get_or_create_water(today)
    water_servings = water['glasses'] or 0
    water_ml = water_servings * WATER_SERVING_ML

    # Current body weight + when it was last recorded
    latest_weight = get_latest_weight()
    if latest_weight:
        current_weight = latest_weight['body_weight']
        last_weight_date = latest_weight['date']
        next_weigh_in = (date.fromisoformat(last_weight_date)
                         + timedelta(days=WEIGHT_CHECK_INTERVAL_DAYS)).isoformat()
    else:
        current_weight = None
        last_weight_date = None
        next_weigh_in = None

    return render_template('index.html',
                           today=today,
                           quote=quote_of_the_day(),
                           workout_exercises=workout_exercises,
                           workout_dates=workout_dates,
                           total_calories=total_calories,
                           total_protein=total_protein,
                           total_carbs=total_carbs,
                           total_fat=total_fat,
                           targets=current_targets(),
                           meals_count=len(meals),
                           water_servings=water_servings,
                           water_ml=water_ml,
                           water_target_ml=WATER_TARGET_ML,
                           water_target_servings=WATER_TARGET_SERVINGS,
                           current_weight=current_weight,
                           last_weight_date=last_weight_date,
                           next_weigh_in=next_weigh_in,
                           routine=routine_context(),
                           today_is_workout=is_today_workout())


@app.route('/log')
def log_workout():
    day = resolve_date()
    workout = get_workout(day)  # read-only: don't create empty rows while browsing
    exercises = get_exercises()
    workout_exercises = get_workout_exercises(workout['id']) if workout else []

    return render_template('workout.html',
                           nav=date_nav(day),
                           exercises=exercises,
                           workout_exercises=workout_exercises)

@app.route('/exercises', methods=['GET', 'POST'])
def exercises():
    if request.method == 'POST':
        name = request.form['name']
        body_part = request.form['body_part']
        default_sets = int(request.form['default_sets']) if request.form['default_sets'] else 3
        default_reps = int(request.form['default_reps']) if request.form['default_reps'] else 10
        add_exercise(name, body_part, default_sets, default_reps)
        return redirect(url_for('exercises'))

    exercises = get_exercises()
    return render_template('exercises.html', exercises=exercises)

@app.route('/exercises/<int:exercise_id>/delete', methods=['POST'])
def delete_exercise_route(exercise_id):
    delete_exercise(exercise_id)
    return redirect(url_for('exercises'))

@app.route('/workout', methods=['POST'])
def add_exercise_to_workout():
    day = resolve_date()
    workout = get_or_create_workout(day)
    exercise_id = request.form['exercise_id']
    sets = int(request.form['sets']) if request.form['sets'] else 3
    reps = int(request.form['reps']) if request.form['reps'] else 10
    weight = float(request.form['weight']) if request.form['weight'] else 0

    add_workout_exercise(workout['id'], exercise_id, sets, reps, weight)
    return redirect(url_for('log_workout', date=day))

@app.route('/workout/delete/<int:we_id>', methods=['POST'])
def delete_workout_exercise_route(we_id):
    delete_workout_exercise(we_id)
    return redirect(url_for('log_workout', date=resolve_date()))

@app.route('/workout/toggle/<int:we_id>', methods=['POST'])
def toggle_exercise(we_id):
    new_status = toggle_exercise_completion(we_id)
    return jsonify({'completed': new_status})

@app.route('/workout/update/<int:we_id>', methods=['POST'])
def update_exercise(we_id):
    sets = int(request.form['sets'])
    reps = int(request.form['reps'])
    weight = float(request.form['weight']) if request.form['weight'] else 0
    update_workout_exercise(we_id, sets, reps, weight)
    return jsonify({'success': True})

@app.route('/weight', methods=['GET', 'POST'])
def weight():
    today = date.today().isoformat()
    if request.method == 'POST':
        date_str = request.form['date']
        body_weight = float(request.form['body_weight']) if request.form['body_weight'] else None
        get_or_create_workout(date_str)
        update_workout_weight(date_str, body_weight)
        return redirect(url_for('weight'))

    # Only show dates that actually have a logged weight (most recent first)
    weight_history = [dict(row) for row in get_workout_history(365) if row['body_weight'] is not None]
    return render_template('weight.html', today=today, weight_history=weight_history)

@app.route('/weight/<date_str>/delete', methods=['POST'])
def delete_weight(date_str):
    clear_workout_weight(date_str)
    return redirect(url_for('weight'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    today = date.today().isoformat()
    if request.method == 'POST':
        height_feet = int(request.form['height_feet']) if request.form.get('height_feet') else 0
        height_inches = int(request.form['height_inches']) if request.form.get('height_inches') else 0
        goal = request.form.get('goal', 'maintain')
        activity = request.form.get('activity', 'moderate')
        update_settings(height_feet, height_inches, goal, activity)
        # Optionally update current weight (logs/updates today's weigh-in)
        if request.form.get('weight_kg'):
            get_or_create_workout(today)
            update_workout_weight(today, float(request.form['weight_kg']))
        return redirect(url_for('settings'))

    s = get_settings()
    weight = current_weight_kg()
    height_m = nutrition.height_to_meters(s['height_feet'], s['height_inches'])
    bmi = nutrition.compute_bmi(weight, height_m)

    # Pre-parse the routine for the editor UI
    work_days, rest_days = routine_lib.parse_cycle(s['routine_pattern'] or 'WR')

    return render_template('settings.html',
                           settings=s,
                           current_weight=weight,
                           bmi=bmi,
                           bmi_category=nutrition.bmi_category(bmi),
                           targets=current_targets(),
                           goal_labels=nutrition.GOAL_LABELS,
                           activity_labels=nutrition.ACTIVITY_LABELS,
                           today=today,
                           routine=routine_context(),
                           routine_weekdays=routine_lib.parse_weekly(s['routine_pattern'] or ''),
                           routine_work_days=work_days,
                           routine_rest_days=rest_days,
                           weekday_labels=routine_lib.WEEKDAYS)

@app.route('/settings/routine', methods=['POST'])
def save_routine():
    mode = request.form.get('routine_mode', 'cycle')
    name = (request.form.get('routine_name') or '').strip() or 'My Routine'
    if mode == 'weekly':
        days = [int(d) for d in request.form.getlist('weekday')]
        pattern = routine_lib.build_weekly_pattern(days)
        start = '2026-01-01'  # unused for weekly, but keep a valid anchor
    else:
        work = int(request.form['work_days']) if request.form.get('work_days') else 1
        rest = int(request.form['rest_days']) if request.form.get('rest_days') else 1
        pattern = routine_lib.build_cycle_pattern(work, rest)
        start = request.form.get('routine_start') or date.today().isoformat()
    update_routine(mode, pattern, start, name)
    return redirect(url_for('settings'))

@app.route('/water', methods=['GET', 'POST'])
def water():
    day = resolve_date()
    if request.method == 'POST':
        # action: 'add' (+500ml) or 'remove' (-500ml)
        action = request.form.get('action', 'add')
        delta = 1 if action == 'add' else -1
        increment_water(day, delta)
        return redirect(url_for('water', date=day))

    water = get_water(day)  # read-only: don't create empty rows while browsing
    servings = (water['glasses'] if water else 0) or 0
    return render_template('water.html',
                           nav=date_nav(day),
                           servings=servings,
                           water_ml=servings * WATER_SERVING_ML,
                           serving_ml=WATER_SERVING_ML,
                           target_ml=WATER_TARGET_ML,
                           target_servings=WATER_TARGET_SERVINGS,
                           goal_reached=servings >= WATER_TARGET_SERVINGS)

@app.route('/meals', methods=['GET', 'POST'])
def meals():
    day = resolve_date()
    if request.method == 'POST':
        name = request.form['name']
        calories = int(request.form['calories']) if request.form['calories'] else 0
        protein = int(request.form['protein']) if request.form['protein'] else 0
        carbs = int(request.form['carbs']) if request.form.get('carbs') else 0
        fat = int(request.form['fat']) if request.form.get('fat') else 0
        add_meal(day, name, calories, protein, carbs, fat)
        return redirect(url_for('meals', date=day))

    meals = get_meals(day)
    templates = get_meal_templates()
    totals = {
        'calories': sum(m['calories'] or 0 for m in meals),
        'protein': sum(m['protein'] or 0 for m in meals),
        'carbs': sum(m['carbs'] or 0 for m in meals),
        'fat': sum(m['fat'] or 0 for m in meals),
    }

    return render_template('meals.html',
                         nav=date_nav(day),
                         meals=meals,
                         templates=templates,
                         totals=totals,
                         targets=current_targets())

@app.route('/meals/template/<int:template_id>/add', methods=['POST'])
def add_meal_template_route(template_id):
    day = resolve_date()
    add_meal_from_template(day, template_id)
    return redirect(url_for('meals', date=day))

@app.route('/meals/template', methods=['POST'])
def create_meal_template_route():
    name = request.form['name']
    calories = int(request.form['calories']) if request.form['calories'] else 0
    protein = int(request.form['protein']) if request.form['protein'] else 0
    carbs = int(request.form['carbs']) if request.form.get('carbs') else 0
    fat = int(request.form['fat']) if request.form.get('fat') else 0
    add_meal_template(name, calories, protein, carbs, fat)
    return redirect(url_for('meals', date=resolve_date()))

@app.route('/meals/template/<int:template_id>/delete', methods=['POST'])
def delete_meal_template_route(template_id):
    delete_meal_template(template_id)
    return redirect(url_for('meals', date=resolve_date()))

@app.route('/meals/<int:meal_id>/delete', methods=['POST'])
def delete_meal_route(meal_id):
    delete_meal(meal_id)
    return redirect(url_for('meals', date=resolve_date()))

@app.route('/progress')
def progress():
    weight_history = [dict(row) for row in get_workout_history(90)]
    exercises = [dict(row) for row in get_exercises()]
    workout_dates = get_logged_workout_dates(365)
    detailed_workout_history = get_detailed_workout_history(30)

    # Get progress for each exercise (convert Rows to dicts so it's JSON-serializable)
    exercise_progress = {}
    for exercise in exercises:
        exercise_progress[exercise['id']] = {
            'name': exercise['name'],
            'data': [dict(row) for row in get_exercise_progress(exercise['id'], 30)]
        }

    return render_template('progress.html',
                         workout_history=weight_history,
                         exercises=exercises,
                         exercise_progress=exercise_progress,
                         workout_dates=workout_dates,
                         detailed_workout_history=detailed_workout_history,
                         routine=routine_context())

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
