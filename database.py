import sqlite3
from datetime import date

DB_NAME = 'workout.db'

# Ready-made meals you eat often. (name, calories, protein, carbs, fat)
DEFAULT_MEAL_TEMPLATES = [
    ('Chicken Breast (200g)', 330, 62, 0, 7),
    ('3 Whole Eggs', 215, 19, 1, 15),
    ('Rice Bowl (1 cup)', 205, 4, 45, 0),
    ('Protein Shake (1 scoop)', 120, 25, 3, 2),
    ('Greek Yogurt (170g)', 100, 17, 6, 0),
    ('Oatmeal (1 cup)', 300, 11, 54, 5),
    ('Salmon Fillet (150g)', 280, 39, 0, 13),
    ('Banana', 105, 1, 27, 0),
    ('Peanut Butter (2 tbsp)', 190, 8, 7, 16),
    ('Tuna Can (in water)', 120, 26, 0, 1),
]

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(cursor, table, column):
    cursor.execute(f'PRAGMA table_info({table})')
    return any(row['name'] == column for row in cursor.fetchall())

def _migrate(cursor):
    """Add columns introduced after the original schema, for existing DBs."""
    for table in ('meals', 'meal_templates'):
        for col in ('carbs', 'fat'):
            if not _column_exists(cursor, table, col):
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} INTEGER DEFAULT 0')
    # Routine columns on settings (added after the original settings schema)
    routine_cols = [
        ('routine_mode', "TEXT DEFAULT 'cycle'"),
        ('routine_pattern', "TEXT DEFAULT 'WR'"),
        ('routine_start', "TEXT DEFAULT '2026-01-01'"),
        ('routine_name', "TEXT DEFAULT 'Alternate Days'"),
    ]
    for col, decl in routine_cols:
        if not _column_exists(cursor, 'settings', col):
            cursor.execute(f'ALTER TABLE settings ADD COLUMN {col} {decl}')

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Exercises table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            body_part TEXT NOT NULL,
            default_sets INTEGER DEFAULT 3,
            default_reps INTEGER DEFAULT 10
        )
    ''')
    
    # Workouts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            body_weight REAL
        )
    ''')
    
    # Workout exercises table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,
            sets INTEGER,
            reps INTEGER,
            weight REAL,
            completed BOOLEAN DEFAULT 0,
            timestamp TEXT,
            FOREIGN KEY (workout_id) REFERENCES workouts(id),
            FOREIGN KEY (exercise_id) REFERENCES exercises(id)
        )
    ''')
    
    # Water intake table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_intake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            glasses INTEGER DEFAULT 0
        )
    ''')
    
    # Meals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            name TEXT NOT NULL,
            calories INTEGER,
            protein INTEGER,
            carbs INTEGER DEFAULT 0,
            fat INTEGER DEFAULT 0
        )
    ''')

    # Meal templates table (ready-made meals to add with one click)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            calories INTEGER DEFAULT 0,
            protein INTEGER DEFAULT 0,
            carbs INTEGER DEFAULT 0,
            fat INTEGER DEFAULT 0
        )
    ''')

    # Settings table (single row of profile info for nutrition targets / BMI)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            height_feet INTEGER DEFAULT 0,
            height_inches INTEGER DEFAULT 0,
            goal TEXT DEFAULT 'maintain',
            activity TEXT DEFAULT 'moderate',
            routine_mode TEXT DEFAULT 'cycle',
            routine_pattern TEXT DEFAULT 'WR',
            routine_start TEXT DEFAULT '2026-01-01',
            routine_name TEXT DEFAULT 'Alternate Days'
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO settings (id) VALUES (1)')

    # Bring older databases up to date (adds carbs/fat columns if missing)
    _migrate(cursor)

    conn.commit()
    
    # Add default exercises if none exist
    cursor.execute('SELECT COUNT(*) FROM exercises')
    if cursor.fetchone()[0] == 0:
        default_exercises = [
            ('Shoulder Press', 'shoulders', 4, 12),
            ('Lateral Raises', 'shoulders', 3, 12),
            ('Front Raises', 'shoulders', 3, 10),
            ('Rear Delt Flys', 'shoulders', 3, 12),
            ('Pull-ups', 'back', 4, 10),
            ('Lat Pulldowns', 'back', 4, 12),
            ('Bent Over Rows', 'back', 4, 10),
            ('Face Pulls', 'back', 3, 12),
            ('Deadlifts', 'back', 4, 6),
            ('Seated Cable Rows', 'back', 3, 12)
        ]
        for name, body_part, sets, reps in default_exercises:
            cursor.execute('INSERT INTO exercises (name, body_part, default_sets, default_reps) VALUES (?, ?, ?, ?)',
                          (name, body_part, sets, reps))
        conn.commit()

    # Seed default meal templates, or backfill macros on an already-seeded DB
    cursor.execute('SELECT COUNT(*) FROM meal_templates')
    if cursor.fetchone()[0] == 0:
        for name, calories, protein, carbs, fat in DEFAULT_MEAL_TEMPLATES:
            cursor.execute(
                'INSERT INTO meal_templates (name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?)',
                (name, calories, protein, carbs, fat))
    else:
        # Older seeded templates may have NULL/0 carbs+fat — fill in the known macros by name
        for name, calories, protein, carbs, fat in DEFAULT_MEAL_TEMPLATES:
            cursor.execute('''
                UPDATE meal_templates SET carbs = ?, fat = ?
                WHERE name = ? AND (carbs IS NULL OR carbs = 0) AND (fat IS NULL OR fat = 0)
            ''', (carbs, fat, name))
    conn.commit()

    conn.close()

def add_exercise(name, body_part, default_sets=3, default_reps=10):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO exercises (name, body_part, default_sets, default_reps) VALUES (?, ?, ?, ?)',
                   (name, body_part, default_sets, default_reps))
    conn.commit()
    conn.close()

def get_exercises():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM exercises ORDER BY body_part, name')
    exercises = cursor.fetchall()
    conn.close()
    return exercises

def delete_exercise(exercise_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM exercises WHERE id = ?', (exercise_id,))
    conn.commit()
    conn.close()

def get_workout(date_str):
    """Fetch a workout for a date WITHOUT creating one (read-only browsing)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM workouts WHERE date = ?', (date_str,))
    workout = cursor.fetchone()
    conn.close()
    return workout

def get_or_create_workout(date_str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM workouts WHERE date = ?', (date_str,))
    workout = cursor.fetchone()
    
    if not workout:
        cursor.execute('INSERT INTO workouts (date) VALUES (?)', (date_str,))
        conn.commit()
        cursor.execute('SELECT * FROM workouts WHERE date = ?', (date_str,))
        workout = cursor.fetchone()
    
    conn.close()
    return workout

def update_workout_weight(date_str, body_weight):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE workouts SET body_weight = ? WHERE date = ?', (body_weight, date_str))
    conn.commit()
    conn.close()

def clear_workout_weight(date_str):
    """Remove the body weight for a given date (keeps the workout row)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE workouts SET body_weight = NULL WHERE date = ?', (date_str,))
    conn.commit()
    conn.close()

def add_workout_exercise(workout_id, exercise_id, sets, reps, weight):
    from datetime import datetime
    conn = get_db()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO workout_exercises (workout_id, exercise_id, sets, reps, weight, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (workout_id, exercise_id, sets, reps, weight, timestamp))
    conn.commit()
    conn.close()

def get_workout_exercises(workout_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT we.*, e.name, e.body_part 
        FROM workout_exercises we
        JOIN exercises e ON we.exercise_id = e.id
        WHERE we.workout_id = ?
    ''', (workout_id,))
    exercises = cursor.fetchall()
    conn.close()
    return exercises

def toggle_exercise_completion(we_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT completed FROM workout_exercises WHERE id = ?', (we_id,))
    current = cursor.fetchone()
    new_status = 0 if current['completed'] else 1
    cursor.execute('UPDATE workout_exercises SET completed = ? WHERE id = ?', (new_status, we_id))
    conn.commit()
    conn.close()
    return new_status

def update_workout_exercise(we_id, sets, reps, weight):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE workout_exercises
        SET sets = ?, reps = ?, weight = ?
        WHERE id = ?
    ''', (sets, reps, weight, we_id))
    conn.commit()
    conn.close()

def delete_workout_exercise(we_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM workout_exercises WHERE id = ?', (we_id,))
    conn.commit()
    conn.close()

def get_water(date_str):
    """Fetch water for a date WITHOUT creating a row (read-only browsing)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM water_intake WHERE date = ?', (date_str,))
    water = cursor.fetchone()
    conn.close()
    return water

def get_or_create_water(date_str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM water_intake WHERE date = ?', (date_str,))
    water = cursor.fetchone()
    
    if not water:
        cursor.execute('INSERT INTO water_intake (date, glasses) VALUES (?, 0)', (date_str,))
        conn.commit()
        cursor.execute('SELECT * FROM water_intake WHERE date = ?', (date_str,))
        water = cursor.fetchone()
    
    conn.close()
    return water

def update_water(date_str, glasses):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE water_intake SET glasses = ? WHERE date = ?', (glasses, date_str))
    conn.commit()
    conn.close()

def increment_water(date_str, delta):
    """Add `delta` 500ml servings to today's water (never below 0)."""
    get_or_create_water(date_str)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT glasses FROM water_intake WHERE date = ?', (date_str,))
    current = cursor.fetchone()['glasses'] or 0
    new_total = max(0, current + delta)
    cursor.execute('UPDATE water_intake SET glasses = ? WHERE date = ?', (new_total, date_str))
    conn.commit()
    conn.close()
    return new_total

def add_meal(date_str, name, calories, protein, carbs=0, fat=0):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO meals (date, name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?)',
                   (date_str, name, calories, protein, carbs, fat))
    conn.commit()
    conn.close()

def get_meals(date_str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM meals WHERE date = ? ORDER BY id', (date_str,))
    meals = cursor.fetchall()
    conn.close()
    return meals

def delete_meal(meal_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM meals WHERE id = ?', (meal_id,))
    conn.commit()
    conn.close()

def get_meal_templates():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM meal_templates ORDER BY name')
    templates = cursor.fetchall()
    conn.close()
    return templates

def add_meal_template(name, calories=0, protein=0, carbs=0, fat=0):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO meal_templates (name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?)',
                   (name, calories, protein, carbs, fat))
    conn.commit()
    conn.close()

def delete_meal_template(template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM meal_templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()

def add_meal_from_template(date_str, template_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, calories, protein, carbs, fat FROM meal_templates WHERE id = ?', (template_id,))
    template = cursor.fetchone()
    conn.close()
    if template:
        add_meal(date_str, template['name'], template['calories'], template['protein'],
                 template['carbs'] or 0, template['fat'] or 0)

def get_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings WHERE id = 1')
    settings = cursor.fetchone()
    conn.close()
    return settings

def update_settings(height_feet, height_inches, goal, activity):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings
        SET height_feet = ?, height_inches = ?, goal = ?, activity = ?
        WHERE id = 1
    ''', (height_feet, height_inches, goal, activity))
    conn.commit()
    conn.close()

def update_routine(mode, pattern, start, name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings
        SET routine_mode = ?, routine_pattern = ?, routine_start = ?, routine_name = ?
        WHERE id = 1
    ''', (mode, pattern, start, name))
    conn.commit()
    conn.close()

def get_latest_weight():
    """Return the most recent workout row that has a body_weight, or None."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, body_weight
        FROM workouts
        WHERE body_weight IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    return row

def get_workout_history(days=30):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date, body_weight 
        FROM workouts 
        ORDER BY date DESC 
        LIMIT ?
    ''', (days,))
    history = cursor.fetchall()
    conn.close()
    return history

def get_exercise_progress(exercise_id, days=30):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.date, we.weight, we.reps, we.sets
        FROM workout_exercises we
        JOIN workouts w ON we.workout_id = w.id
        WHERE we.exercise_id = ?
        ORDER BY w.date DESC
        LIMIT ?
    ''', (exercise_id, days))
    progress = cursor.fetchall()
    conn.close()
    return progress

def get_logged_workout_dates(days=365):
    """Dates that actually have at least one logged exercise (true workouts)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT w.date
        FROM workouts w
        JOIN workout_exercises we ON we.workout_id = w.id
        ORDER BY w.date DESC
        LIMIT ?
    ''', (days,))
    dates = [row['date'] for row in cursor.fetchall()]
    conn.close()
    return dates

def get_workout_dates(days=365):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT date 
        FROM workouts 
        ORDER BY date DESC 
        LIMIT ?
    ''', (days,))
    dates = [row['date'] for row in cursor.fetchall()]
    conn.close()
    return dates

def get_detailed_workout_history(days=30):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.date, we.id, we.sets, we.reps, we.weight, we.timestamp, e.name, e.body_part
        FROM workouts w
        LEFT JOIN workout_exercises we ON w.id = we.workout_id
        LEFT JOIN exercises e ON we.exercise_id = e.id
        ORDER BY w.date DESC, we.timestamp DESC
        LIMIT ?
    ''', (days * 10,))
    rows = cursor.fetchall()
    conn.close()
    
    # Group by date
    history = {}
    for row in rows:
        date = row['date']
        if date not in history:
            history[date] = {'date': date, 'exercises': []}
        if row['name']:  # Only add if there's an exercise
            history[date]['exercises'].append({
                'name': row['name'],
                'body_part': row['body_part'],
                'sets': row['sets'],
                'reps': row['reps'],
                'weight': row['weight'],
                'timestamp': row['timestamp']
            })
    
    return list(history.values())
