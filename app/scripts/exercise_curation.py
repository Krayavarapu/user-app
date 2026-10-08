"""Curated exercise picks for ``exercises_v1.json``.

Two kinds of rows:

* ``S(...)``  -- derived from an entry of free-exercise-db (Unlicense / public domain, pinned
  commit). Only *facts* are taken from the source: name, muscles, difficulty, equipment. Its
  instruction text and images are NOT used (their provenance is uncertain).
* ``C(...)``  -- authored in-house to cover gaps in the source (carries, dumbbell hinges,
  bodyweight pulls, ...).

Equipment DSL (``equipment`` argument)::

    ""                      bodyweight (no catalog equipment)
    "dumbbell"              needs a dumbbell
    "barbell+squat_rack"    needs both
    "dumbbell|kettlebell"   either works (separate options)
    BENCH                   expands to flat_bench OR adjustable_bench
    STEP                    expands to plyo_box OR flat_bench OR adjustable_bench

Hand-picked: difficulty overrides, laterality, measure and pattern are judgement calls recorded
here. Contraindication tags, impact level, goal tags and tempo are derived by rule
(``app/services/exercise_library/tagging.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

SQ, HI, LU = "squat", "hinge", "lunge"
HP, VP, HR, VR = "horizontal_push", "vertical_push", "horizontal_pull", "vertical_pull"
CA = "carry"
AE, AR, CF = "core_anti_extension", "core_anti_rotation", "core_flexion"
CO, MO = "conditioning", "mobility"
IU, IL = "isolation_upper", "isolation_lower"

B, U, A = "bilateral", "unilateral", "alternating"


@dataclass(frozen=True)
class Pick:
    name: str
    pattern: str
    laterality: str
    equipment: str
    source: Optional[str] = None  # name in free-exercise-db; None => in-house
    difficulty: Optional[int] = None  # None => from source level
    measure: str = "reps"
    modality: Optional[str] = None  # None => strength / conditioning / mobility by pattern
    impact: Optional[str] = None  # None => derived from the name
    muscles: Tuple[str, ...] = ()  # in-house only
    secondary: Tuple[str, ...] = ()  # in-house only


def S(source: str, name: str, pattern: str, laterality: str, equipment: str = "", **kw) -> Pick:
    return Pick(name=name, pattern=pattern, laterality=laterality, equipment=equipment, source=source, **kw)


def C(name, pattern, laterality, equipment, muscles, secondary=(), **kw) -> Pick:
    return Pick(
        name=name, pattern=pattern, laterality=laterality, equipment=equipment,
        muscles=tuple(muscles), secondary=tuple(secondary), **kw,
    )


T = {"measure": "time"}
WARM = {"modality": "warmup"}

PICKS = [
    # ---------------------------------------------------------------- squat
    S("Bodyweight Squat", "Bodyweight Squat", SQ, B),
    C("Wall Sit", SQ, B, "", ["quads"], ["glutes"], difficulty=1, **T),
    C("Bodyweight Sumo Squat", SQ, B, "", ["quads", "glutes"], ["adductors"], difficulty=1),
    S("Dumbbell Squat", "Dumbbell Squat", SQ, B, "dumbbell"),
    S("Goblet Squat", "Goblet Squat", SQ, B, "dumbbell|kettlebell"),
    S("Plie Dumbbell Squat", "Dumbbell Plie Squat", SQ, B, "dumbbell"),
    S("Dumbbell Squat To A Bench", "Dumbbell Box Squat", SQ, B, "dumbbell+STEP"),
    S("Front Squats With Two Kettlebells", "Double Kettlebell Front Squat", SQ, B, "kettlebell"),
    S("Barbell Squat", "Barbell Back Squat", SQ, B, "barbell+squat_rack", difficulty=2),
    S("Front Barbell Squat", "Barbell Front Squat", SQ, B, "barbell+squat_rack", difficulty=3),
    S("Smith Machine Squat", "Smith Machine Squat", SQ, B, "smith_machine", difficulty=2),
    S("Leg Press", "Leg Press", SQ, B, "leg_press_machine", difficulty=1),
    S("Squats - With Bands", "Banded Squat", SQ, B, "resistance_band", difficulty=1),
    # ---------------------------------------------------------------- hinge
    S("Barbell Deadlift", "Barbell Deadlift", HI, B, "barbell", difficulty=2),
    S("Romanian Deadlift", "Barbell Romanian Deadlift", HI, B, "barbell", difficulty=2),
    S("Sumo Deadlift", "Barbell Sumo Deadlift", HI, B, "barbell", difficulty=2),
    S("Good Morning", "Barbell Good Morning", HI, B, "barbell+squat_rack", difficulty=3),
    S("Rack Pulls", "Barbell Rack Pull", HI, B, "barbell+squat_rack", difficulty=2),
    S("Barbell Hip Thrust", "Barbell Hip Thrust", HI, B, "barbell+BENCH", difficulty=2),
    S("Barbell Glute Bridge", "Barbell Glute Bridge", HI, B, "barbell", difficulty=2),
    S("Stiff-Legged Dumbbell Deadlift", "Dumbbell Stiff-Leg Deadlift", HI, B, "dumbbell", difficulty=1),
    C("Dumbbell Romanian Deadlift", HI, B, "dumbbell", ["hamstrings", "glutes"], ["lower_back"], difficulty=1),
    C("Dumbbell Single-Leg Romanian Deadlift", HI, U, "dumbbell", ["hamstrings", "glutes"], ["lower_back"], difficulty=2),
    C("Dumbbell Glute Bridge", HI, B, "dumbbell", ["glutes"], ["hamstrings"], difficulty=1),
    C("Dumbbell Hip Thrust", HI, B, "dumbbell+BENCH", ["glutes"], ["hamstrings"], difficulty=1),
    C("Kettlebell Swing", HI, B, "kettlebell|dumbbell", ["glutes", "hamstrings"], ["lower_back", "delts"], difficulty=2),
    S("One-Arm Kettlebell Swings", "One-Arm Kettlebell Swing", HI, U, "kettlebell", difficulty=2),
    S("Kettlebell One-Legged Deadlift", "Kettlebell Single-Leg Deadlift", HI, U, "kettlebell", difficulty=2),
    S("Butt Lift (Bridge)", "Glute Bridge", HI, B),
    S("Single Leg Glute Bridge", "Single-Leg Glute Bridge", HI, U),
    C("Bodyweight Good Morning", HI, B, "", ["hamstrings", "glutes"], ["lower_back"], difficulty=1),
    S("Hyperextensions With No Hyperextension Bench", "Floor Back Extension", HI, B, difficulty=1),
    S("Band Good Morning", "Banded Good Morning", HI, B, "resistance_band", difficulty=1),
    S("Pull Through", "Cable Pull-Through", HI, B, "cable_machine", difficulty=1),
    S("Cable Deadlifts", "Cable Deadlift", HI, B, "cable_machine", difficulty=1),
    # ---------------------------------------------------------------- lunge
    C("Bodyweight Reverse Lunge", LU, A, "", ["quads", "glutes"], ["hamstrings"], difficulty=1),
    C("Bodyweight Split Squat", LU, U, "", ["quads", "glutes"], ["hamstrings"], difficulty=1),
    C("Bodyweight Lateral Lunge", LU, A, "", ["quads", "glutes", "adductors"], ["hamstrings"], difficulty=1),
    S("Bodyweight Walking Lunge", "Bodyweight Walking Lunge", LU, A, difficulty=1),
    S("Dumbbell Lunges", "Dumbbell Lunge", LU, A, "dumbbell", difficulty=1),
    S("Dumbbell Rear Lunge", "Dumbbell Reverse Lunge", LU, A, "dumbbell", difficulty=1),
    S("Split Squat with Dumbbells", "Dumbbell Split Squat", LU, U, "dumbbell", difficulty=1),
    S("Dumbbell Step Ups", "Dumbbell Step-Up", LU, U, "dumbbell+STEP", difficulty=1),
    C("Dumbbell Bulgarian Split Squat", LU, U, "dumbbell+STEP", ["quads", "glutes"], ["hamstrings"], difficulty=2),
    S("Barbell Lunge", "Barbell Lunge", LU, A, "barbell+squat_rack", difficulty=2),
    S("Barbell Walking Lunge", "Barbell Walking Lunge", LU, A, "barbell+squat_rack", difficulty=2),
    S("Smith Single-Leg Split Squat", "Smith Machine Split Squat", LU, U, "smith_machine", difficulty=2),
    # ------------------------------------------------------- horizontal push
    S("Pushups", "Push-Up", HP, B, difficulty=1),
    S("Incline Push-Up", "Incline Push-Up", HP, B, difficulty=1),
    S("Push-Ups - Close Triceps Position", "Close-Grip Push-Up", HP, B, difficulty=2),
    S("Push-Up Wide", "Wide-Grip Push-Up", HP, B, difficulty=1),
    S("Decline Push-Up", "Decline Push-Up", HP, B, difficulty=2),
    S("Single-Arm Push-Up", "Single-Arm Push-Up", HP, U, difficulty=3),
    S("Push Up to Side Plank", "Push-Up to Side Plank", HP, A, difficulty=2),
    S("Bench Dips", "Bench Dip", HP, B, "STEP", difficulty=1),
    S("Dumbbell Bench Press", "Dumbbell Bench Press", HP, B, "dumbbell+BENCH", difficulty=1),
    S("Incline Dumbbell Press", "Incline Dumbbell Press", HP, B, "dumbbell+adjustable_bench", difficulty=1),
    S("Dumbbell Floor Press", "Dumbbell Floor Press", HP, B, "dumbbell", difficulty=1),
    S("One Arm Dumbbell Bench Press", "One-Arm Dumbbell Bench Press", HP, U, "dumbbell+BENCH", difficulty=2),
    S("Barbell Bench Press - Medium Grip", "Barbell Bench Press", HP, B, "barbell+squat_rack+BENCH", difficulty=2),
    S("Barbell Incline Bench Press - Medium Grip", "Barbell Incline Bench Press", HP, B, "barbell+squat_rack+adjustable_bench", difficulty=2),
    S("Close-Grip Barbell Bench Press", "Close-Grip Barbell Bench Press", HP, B, "barbell+squat_rack+BENCH", difficulty=2),
    S("Floor Press", "Barbell Floor Press", HP, B, "barbell+squat_rack", difficulty=2),
    S("Machine Bench Press", "Machine Chest Press", HP, B, "chest_press_machine", difficulty=1),
    S("Smith Machine Bench Press", "Smith Machine Bench Press", HP, B, "smith_machine+BENCH", difficulty=2),
    S("Cable Chest Press", "Cable Chest Press", HP, B, "cable_machine", difficulty=1),
    S("Incline Cable Chest Press", "Incline Cable Chest Press", HP, B, "cable_machine+adjustable_bench", difficulty=1),
    S("Bench Press - With Bands", "Banded Chest Press", HP, B, "resistance_band", difficulty=1),
    S("Alternating Floor Press", "Kettlebell Alternating Floor Press", HP, A, "kettlebell", difficulty=1),
    # --------------------------------------------------------- vertical push
    S("Standing Military Press", "Barbell Standing Overhead Press", VP, B, "barbell+squat_rack", difficulty=2),
    S("Seated Barbell Military Press", "Barbell Seated Overhead Press", VP, B, "barbell+squat_rack+adjustable_bench", difficulty=2),
    S("Dumbbell Shoulder Press", "Dumbbell Shoulder Press", VP, B, "dumbbell", difficulty=1),
    S("Arnold Dumbbell Press", "Arnold Press", VP, B, "dumbbell", difficulty=2),
    S("Seated Dumbbell Press", "Seated Dumbbell Shoulder Press", VP, B, "dumbbell+adjustable_bench", difficulty=1),
    S("Dumbbell One-Arm Shoulder Press", "One-Arm Dumbbell Shoulder Press", VP, U, "dumbbell", difficulty=2),
    S("Alternating Kettlebell Press", "Kettlebell Alternating Press", VP, A, "kettlebell", difficulty=2),
    S("Two-Arm Kettlebell Military Press", "Double Kettlebell Press", VP, B, "kettlebell", difficulty=2),
    S("Smith Machine Overhead Shoulder Press", "Smith Machine Shoulder Press", VP, B, "smith_machine", difficulty=2),
    S("Cable Shoulder Press", "Cable Shoulder Press", VP, B, "cable_machine", difficulty=1),
    S("Shoulder Press - With Bands", "Banded Shoulder Press", VP, B, "resistance_band", difficulty=1),
    S("Handstand Push-Ups", "Handstand Push-Up", VP, B, difficulty=3),
    C("Pike Push-Up", VP, B, "", ["delts", "triceps"], ["chest"], difficulty=2),
    # ------------------------------------------------------- horizontal pull
    S("Bent Over Barbell Row", "Barbell Bent-Over Row", HR, B, "barbell", difficulty=2),
    S("T-Bar Row with Handle", "T-Bar Row", HR, B, "barbell", difficulty=2),
    S("One-Arm Dumbbell Row", "One-Arm Dumbbell Row", HR, U, "dumbbell", difficulty=1),
    S("Bent Over Two-Dumbbell Row", "Bent-Over Dumbbell Row", HR, B, "dumbbell", difficulty=1),
    S("Dumbbell Incline Row", "Chest-Supported Dumbbell Row", HR, B, "dumbbell+adjustable_bench", difficulty=1),
    C("Dumbbell Renegade Row", HR, A, "dumbbell", ["lats", "mid_back"], ["abs", "delts"], difficulty=3),
    S("One-Arm Kettlebell Row", "One-Arm Kettlebell Row", HR, U, "kettlebell", difficulty=1),
    S("Seated Cable Rows", "Seated Cable Row", HR, B, "cable_machine", difficulty=1),
    S("Seated One-arm Cable Pulley Rows", "One-Arm Seated Cable Row", HR, U, "cable_machine", difficulty=1),
    S("Face Pull", "Cable Face Pull", HR, B, "cable_machine", difficulty=1),
    S("Leverage Iso Row", "Machine Row", HR, B, "seated_row_machine", difficulty=1),
    S("Suspended Row", "Suspension Trainer Row", HR, B, "suspension_trainer", difficulty=1),
    S("Band Pull Apart", "Band Pull-Apart", HR, B, "resistance_band", difficulty=1),
    C("Banded Row", HR, B, "resistance_band", ["lats", "mid_back"], ["biceps"], difficulty=1),
    C("Prone T Raise", HR, B, "", ["rear_delts", "mid_back"], ["traps"], difficulty=1),
    C("Prone W Raise", HR, B, "", ["rear_delts", "mid_back"], ["traps"], difficulty=1),
    C("Reverse Snow Angel", HR, B, "", ["rear_delts", "upper_back"], ["traps"], difficulty=1),
    # --------------------------------------------------------- vertical pull
    S("Pullups", "Pull-Up", VR, B, "pull_up_bar", difficulty=2),
    S("Chin-Up", "Chin-Up", VR, B, "pull_up_bar", difficulty=2),
    S("V-Bar Pullup", "Neutral-Grip Pull-Up", VR, B, "pull_up_bar", difficulty=2),
    S("Band Assisted Pull-Up", "Band-Assisted Pull-Up", VR, B, "pull_up_bar+resistance_band", difficulty=1),
    S("Scapular Pull-Up", "Scapular Pull-Up", VR, B, "pull_up_bar", difficulty=1),
    S("Wide-Grip Lat Pulldown", "Wide-Grip Lat Pulldown", VR, B, "lat_pulldown_machine|cable_machine", difficulty=1),
    S("Underhand Cable Pulldowns", "Underhand Lat Pulldown", VR, B, "lat_pulldown_machine|cable_machine", difficulty=1),
    S("V-Bar Pulldown", "V-Bar Lat Pulldown", VR, B, "lat_pulldown_machine|cable_machine", difficulty=1),
    S("One Arm Lat Pulldown", "One-Arm Lat Pulldown", VR, U, "cable_machine", difficulty=1),
    S("Straight-Arm Pulldown", "Straight-Arm Pulldown", VR, B, "cable_machine", difficulty=1),
    S("Straight-Arm Dumbbell Pullover", "Straight-Arm Dumbbell Pullover", VR, B, "dumbbell+BENCH", difficulty=2),
    C("Dumbbell Pullover", VR, B, "dumbbell+BENCH", ["lats", "chest"], ["triceps", "delts"], difficulty=2),
    C("Floor Dumbbell Pullover", VR, B, "dumbbell", ["lats", "chest"], ["triceps", "delts"], difficulty=1),
    # ----------------------------------------------------------------- carry
    C("Farmer's Carry", CA, B, "dumbbell|kettlebell", ["forearms", "traps", "core"], ["glutes"], difficulty=1, **T),
    C("Suitcase Carry", CA, U, "dumbbell|kettlebell", ["obliques", "forearms", "traps"], ["glutes"], difficulty=1, **T),
    C("Single-Arm Front Rack Carry", CA, U, "dumbbell|kettlebell", ["core", "delts", "forearms"], ["obliques"], difficulty=2, **T),
    C("Overhead Carry", CA, U, "dumbbell|kettlebell", ["delts", "core", "traps"], ["triceps"], difficulty=2, **T),
    C("Sandbag Bear-Hug Carry", CA, B, "sandbag", ["core", "upper_back", "biceps"], ["glutes"], difficulty=2, **T),
    # ----------------------------------------------------- core: anti-extension
    S("Plank", "Forearm Plank", AE, B, difficulty=1, **T),
    S("Dead Bug", "Dead Bug", AE, A, difficulty=1),
    C("Hollow Hold", AE, B, "", ["abs"], ["hip_flexors"], difficulty=2, **T),
    S("Ab Roller", "Ab Wheel Rollout", AE, B, "ab_wheel", difficulty=3),
    S("Suspended Fallout", "Suspension Trainer Fallout", AE, B, "suspension_trainer", difficulty=2),
    # ----------------------------------------------------- core: anti-rotation
    S("Pallof Press", "Cable Pallof Press", AR, B, "cable_machine", difficulty=1),
    S("Pallof Press With Rotation", "Cable Pallof Press with Rotation", AR, A, "cable_machine", difficulty=2),
    S("Side Bridge", "Side Plank", AR, U, difficulty=1, **T),
    C("Bird Dog", AR, A, "", ["abs", "lower_back", "glutes"], ["delts"], difficulty=1),
    C("Plank Shoulder Taps", AR, A, "", ["abs", "obliques"], ["delts"], difficulty=2),
    C("Banded Pallof Press", AR, B, "resistance_band", ["obliques", "abs"], [], difficulty=1),
    # ---------------------------------------------------------- core: flexion
    S("Crunches", "Crunch", CF, B, difficulty=1),
    S("Reverse Crunch", "Reverse Crunch", CF, B, difficulty=1),
    S("Sit-Up", "Sit-Up", CF, B, difficulty=1),
    S("Bent-Knee Hip Raise", "Bent-Knee Hip Raise", CF, B, difficulty=1),
    S("Flutter Kicks", "Flutter Kicks", CF, A, difficulty=1, **T),
    S("Russian Twist", "Russian Twist", CF, A, difficulty=2),
    S("Air Bike", "Bicycle Crunch", CF, A, difficulty=1),
    S("Hanging Leg Raise", "Hanging Leg Raise", CF, B, "pull_up_bar", difficulty=3),
    S("Cable Crunch", "Cable Crunch", CF, B, "cable_machine", difficulty=1),
    S("Cable Russian Twists", "Cable Russian Twist", CF, A, "cable_machine", difficulty=2),
    S("Standing Cable Wood Chop", "Cable Wood Chop", CF, A, "cable_machine", difficulty=1),
    S("Exercise Ball Crunch", "Stability Ball Crunch", CF, B, "stability_ball", difficulty=1),
    S("Dumbbell Side Bend", "Dumbbell Side Bend", CF, A, "dumbbell", difficulty=1),
    # ---------------------------------------------------------- conditioning
    S("Mountain Climbers", "Mountain Climber", CO, A, difficulty=1, **T),
    C("Jumping Jacks", CO, B, "", ["full_body"], ["calves"], difficulty=1, **T),
    C("High Knees", CO, A, "", ["quads", "hip_flexors"], ["calves", "abs"], difficulty=1, **T),
    C("Burpee", CO, B, "", ["full_body"], [], difficulty=2),
    C("Skaters", CO, A, "", ["glutes", "quads", "abductors"], ["calves"], difficulty=2, **T),
    S("Star Jump", "Star Jump", CO, B, difficulty=1),
    S("Standing Long Jump", "Standing Long Jump", CO, B, difficulty=2),
    S("Freehand Jump Squat", "Jump Squat", CO, B, difficulty=2),
    S("Split Jump", "Split Jump", CO, A, difficulty=2),
    S("Front Box Jump", "Box Jump", CO, B, "plyo_box", difficulty=2),
    S("Rope Jumping", "Jump Rope", CO, B, "jump_rope", difficulty=1, **T),
    S("Overhead Slam", "Medicine Ball Slam", CO, B, "medicine_ball", difficulty=1),
    S("Jogging, Treadmill", "Treadmill Jog", CO, B, "treadmill", difficulty=1, **T),
    S("Walking, Treadmill", "Treadmill Walk", CO, B, "treadmill", difficulty=1, **T),
    S("Rowing, Stationary", "Rowing Machine", CO, B, "rowing_machine", difficulty=1, **T),
    S("Elliptical Trainer", "Elliptical", CO, B, "elliptical", difficulty=1, **T),
    S("Bicycling, Stationary", "Stationary Bike", CO, B, "stationary_bike", difficulty=1, **T),
    # ----------------------------------------------- mobility: dynamic / warm-up
    S("World's Greatest Stretch", "World's Greatest Stretch", MO, A, difficulty=1, **WARM),
    S("Inchworm", "Inchworm", MO, B, difficulty=1, **WARM),
    S("Arm Circles", "Arm Circles", MO, B, difficulty=1, **WARM),
    S("Shoulder Circles", "Shoulder Circles", MO, B, difficulty=1, **WARM),
    S("Standing Hip Circles", "Standing Hip Circles", MO, A, difficulty=1, **WARM),
    S("Ankle Circles", "Ankle Circles", MO, A, difficulty=1, **WARM),
    S("Cat Stretch", "Cat-Cow", MO, B, difficulty=1, **WARM),
    S("Dynamic Chest Stretch", "Dynamic Chest Stretch", MO, B, difficulty=1, **WARM),
    S("Dynamic Back Stretch", "Dynamic Back Stretch", MO, B, difficulty=1, **WARM),
    S("Windmills", "Windmill Reach", MO, A, difficulty=1, **WARM),
    S("Groiners", "Groiner", MO, A, difficulty=1, **WARM),
    S("Wrist Circles", "Wrist Circles", MO, B, difficulty=1, **WARM),
    C("Leg Swings", MO, A, "", ["hamstrings", "hip_flexors"], ["glutes"], difficulty=1, **WARM),
    C("Open Book Rotation", MO, A, "", ["thoracic_spine"], ["obliques"], difficulty=1, **WARM),
    S("Quadriceps-SMR", "Foam Roll Quads", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    S("Hamstring-SMR", "Foam Roll Hamstrings", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    S("Calves-SMR", "Foam Roll Calves", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    S("Latissimus Dorsi-SMR", "Foam Roll Lats", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    S("Iliotibial Tract-SMR", "Foam Roll IT Band", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    S("Piriformis-SMR", "Foam Roll Glutes", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    S("Rhomboids-SMR", "Foam Roll Upper Back", MO, B, "foam_roller", difficulty=1, **WARM, **T),
    # ------------------------------------------------- mobility: static stretches
    S("Child's Pose", "Child's Pose", MO, B, difficulty=1, **T),
    S("Kneeling Hip Flexor", "Kneeling Hip Flexor Stretch", MO, U, difficulty=1, **T),
    S("90/90 Hamstring", "Hamstring Stretch (90/90)", MO, U, difficulty=1, **T),
    S("Seated Floor Hamstring Stretch", "Seated Hamstring Stretch", MO, B, difficulty=1, **T),
    S("Standing Gastrocnemius Calf Stretch", "Standing Calf Stretch", MO, U, difficulty=1, **T),
    S("Standing Soleus And Achilles Stretch", "Soleus and Achilles Stretch", MO, U, difficulty=1, **T),
    S("All Fours Quad Stretch", "Quad Stretch", MO, U, difficulty=1, **T),
    S("Knee Across The Body", "Knee Across the Body Stretch", MO, U, difficulty=1, **T),
    S("Hug Knees To Chest", "Hug Knees to Chest", MO, B, difficulty=1, **T),
    S("Triceps Stretch", "Triceps Stretch", MO, U, difficulty=1, **T),
    S("Shoulder Stretch", "Cross-Body Shoulder Stretch", MO, U, difficulty=1, **T),
    S("Upper Back Stretch", "Upper Back Stretch", MO, B, difficulty=1, **T),
    S("Standing Lateral Stretch", "Standing Side Stretch", MO, U, difficulty=1, **T),
    S("Side Neck Stretch", "Side Neck Stretch", MO, U, difficulty=1, **T),
    S("Chin To Chest Stretch", "Chin to Chest Stretch", MO, B, difficulty=1, **T),
    # --------------------------------------------------------- isolation: upper
    S("Dumbbell Bicep Curl", "Dumbbell Biceps Curl", IU, B, "dumbbell", difficulty=1),
    S("Hammer Curls", "Hammer Curl", IU, B, "dumbbell", difficulty=1),
    S("Concentration Curls", "Concentration Curl", IU, U, "dumbbell", difficulty=1),
    S("Incline Dumbbell Curl", "Incline Dumbbell Curl", IU, B, "dumbbell+adjustable_bench", difficulty=1),
    S("Zottman Curl", "Zottman Curl", IU, B, "dumbbell", difficulty=2),
    S("Side Lateral Raise", "Dumbbell Lateral Raise", IU, B, "dumbbell", difficulty=1),
    S("Front Two-Dumbbell Raise", "Dumbbell Front Raise", IU, B, "dumbbell", difficulty=1),
    S("Reverse Flyes", "Dumbbell Rear Delt Fly", IU, B, "dumbbell", difficulty=1),
    S("Dumbbell Shrug", "Dumbbell Shrug", IU, B, "dumbbell", difficulty=1),
    S("Dumbbell Flyes", "Dumbbell Chest Fly", IU, B, "dumbbell+BENCH", difficulty=1),
    S("Tricep Dumbbell Kickback", "Dumbbell Triceps Kickback", IU, U, "dumbbell", difficulty=1),
    S("Standing Dumbbell Triceps Extension", "Standing Dumbbell Overhead Triceps Extension", IU, B, "dumbbell", difficulty=1),
    S("Lying Dumbbell Tricep Extension", "Lying Dumbbell Triceps Extension", IU, B, "dumbbell+BENCH", difficulty=2),
    S("Palms-Up Dumbbell Wrist Curl Over A Bench", "Dumbbell Wrist Curl", IU, B, "dumbbell", difficulty=1),
    S("Barbell Curl", "Barbell Curl", IU, B, "barbell", difficulty=1),
    S("Barbell Shrug", "Barbell Shrug", IU, B, "barbell", difficulty=1),
    S("EZ-Bar Curl", "EZ-Bar Curl", IU, B, "ez_bar", difficulty=1),
    S("EZ-Bar Skullcrusher", "EZ-Bar Skullcrusher", IU, B, "ez_bar+BENCH", difficulty=2),
    S("Triceps Pushdown", "Cable Triceps Pushdown", IU, B, "cable_machine", difficulty=1),
    S("Standing Biceps Cable Curl", "Cable Biceps Curl", IU, B, "cable_machine", difficulty=1),
    S("Cable Rope Overhead Triceps Extension", "Cable Overhead Triceps Extension", IU, B, "cable_machine", difficulty=1),
    S("Cable Crossover", "Cable Crossover", IU, B, "cable_machine", difficulty=1),
    S("Cable Rear Delt Fly", "Cable Rear Delt Fly", IU, B, "cable_machine", difficulty=1),
    S("Standing Low-Pulley Deltoid Raise", "Cable Lateral Raise", IU, U, "cable_machine", difficulty=1),
    S("Lateral Raise - With Bands", "Banded Lateral Raise", IU, B, "resistance_band", difficulty=1),
    S("External Rotation with Band", "Banded External Rotation", IU, U, "resistance_band", difficulty=1),
    S("Back Flyes - With Bands", "Banded Rear Delt Fly", IU, B, "resistance_band", difficulty=1),
    # --------------------------------------------------------- isolation: lower
    S("Standing Dumbbell Calf Raise", "Dumbbell Standing Calf Raise", IL, B, "dumbbell", difficulty=1),
    S("Calf Raises - With Bands", "Banded Calf Raise", IL, B, "resistance_band", difficulty=1),
    C("Bodyweight Calf Raise", IL, B, "", ["calves"], [], difficulty=1),
    C("Single-Leg Calf Raise", IL, U, "", ["calves"], [], difficulty=1),
    S("Leg Extensions", "Machine Leg Extension", IL, B, "leg_extension_machine", difficulty=1),
    S("Lying Leg Curls", "Lying Leg Curl", IL, B, "leg_curl_machine", difficulty=1),
    S("Seated Leg Curl", "Seated Leg Curl", IL, B, "leg_curl_machine", difficulty=1),
    S("Glute Kickback", "Glute Kickback", IL, U, difficulty=1),
    S("Side Leg Raises", "Side-Lying Leg Raise", IL, U, difficulty=1),
    S("One-Legged Cable Kickback", "Cable Glute Kickback", IL, U, "cable_machine", difficulty=2),
    S("Monster Walk", "Banded Monster Walk", IL, A, "resistance_band", difficulty=1),
    S("Ball Leg Curl", "Stability Ball Hamstring Curl", IL, B, "stability_ball", difficulty=2),
]
