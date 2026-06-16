"""Bodyweight-based nutrition targets + BMI.

Targets are driven by the user's *current* bodyweight (latest weigh-in), so they
automatically shift week to week as the logged weight changes.
"""

# Maintenance calories per kg of bodyweight, by activity level.
ACTIVITY_KCAL_PER_KG = {
    'sedentary':   28,   # little/no exercise
    'light':       30,   # 1-3 days/week
    'moderate':    33,   # 3-5 days/week
    'active':      35,   # 6-7 days/week
    'very_active': 38,   # hard training / physical job
}

ACTIVITY_LABELS = {
    'sedentary':   'Sedentary (little exercise)',
    'light':       'Light (1-3 days/week)',
    'moderate':    'Moderate (3-5 days/week)',
    'active':      'Active (6-7 days/week)',
    'very_active': 'Very active (hard training)',
}

# Goal adjusts calories around maintenance, and sets protein per kg.
GOAL_CALORIE_FACTOR = {'cut': 0.80, 'maintain': 1.00, 'bulk': 1.12}
GOAL_PROTEIN_PER_KG = {'cut': 2.2, 'maintain': 1.8, 'bulk': 2.0}
GOAL_LABELS = {
    'cut': 'Cut (lose fat)',
    'maintain': 'Maintain',
    'bulk': 'Bulk (build muscle)',
}

# Macro energy (kcal per gram)
KCAL_PER_G = {'protein': 4, 'carbs': 4, 'fat': 9}
FAT_CALORIE_SHARE = 0.25  # ~25% of calories from fat, rest split to carbs


# A plausible human height floor (3 ft). Anything shorter is treated as "not set"
# so a half-filled form (e.g. inches only) can't produce a nonsensical BMI.
MIN_PLAUSIBLE_INCHES = 36


def height_to_meters(feet, inches):
    feet = feet or 0
    inches = inches or 0
    total_inches = feet * 12 + inches
    if total_inches < MIN_PLAUSIBLE_INCHES:
        return None
    return total_inches * 0.0254


def compute_bmi(weight_kg, height_m):
    if not weight_kg or not height_m:
        return None
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi):
    if bmi is None:
        return None
    if bmi < 18.5:
        return 'Underweight'
    if bmi < 25:
        return 'Normal'
    if bmi < 30:
        return 'Overweight'
    return 'Obese'


def compute_targets(weight_kg, goal='maintain', activity='moderate'):
    """Return daily calorie + macro targets from current bodyweight."""
    if not weight_kg:
        return None

    kcal_per_kg = ACTIVITY_KCAL_PER_KG.get(activity, 33)
    calories = weight_kg * kcal_per_kg * GOAL_CALORIE_FACTOR.get(goal, 1.0)

    protein_g = weight_kg * GOAL_PROTEIN_PER_KG.get(goal, 1.8)
    fat_g = (calories * FAT_CALORIE_SHARE) / KCAL_PER_G['fat']
    carbs_cal = calories - (protein_g * KCAL_PER_G['protein']) - (fat_g * KCAL_PER_G['fat'])
    carbs_g = max(0, carbs_cal) / KCAL_PER_G['carbs']

    return {
        'calories': round(calories),
        'protein': round(protein_g),
        'carbs': round(carbs_g),
        'fat': round(fat_g),
    }
