from . import db
from .models import Exercise


EXERCISES = [
    ("Barbell Back Squat", "quadriceps", ["glutes", "hamstrings"], ["Set the bar across your upper back.", "Brace your trunk and sit down between your hips.", "Drive through your feet to stand tall."]),
    ("Romanian Deadlift", "hamstrings", ["glutes", "lower back"], ["Hold the bar close to your thighs.", "Push your hips back with a neutral spine.", "Stand by driving your hips forward."]),
    ("Conventional Deadlift", "posterior chain", ["glutes", "hamstrings", "back"], ["Stand with the bar over mid-foot.", "Brace and push the floor away.", "Finish tall without leaning back."]),
    ("Barbell Bench Press", "chest", ["triceps", "front deltoids"], ["Set your shoulder blades against the bench.", "Lower the bar under control.", "Press until your arms are straight."]),
    ("Incline Dumbbell Press", "upper chest", ["triceps", "front deltoids"], ["Set a low incline.", "Lower the dumbbells beside your upper chest.", "Press up while keeping your shoulders stable."]),
    ("Push-Up", "chest", ["triceps", "core"], ["Keep a straight line from head to heel.", "Lower your chest with control.", "Push the floor away."]),
    ("Pull-Up", "back", ["biceps", "forearms"], ["Start from a controlled hang.", "Pull your elbows toward your sides.", "Lower without dropping."]),
    ("Lat Pulldown", "back", ["biceps", "rear deltoids"], ["Brace your torso.", "Pull the bar toward your upper chest.", "Return to full reach with control."]),
    ("Seated Cable Row", "back", ["biceps", "rear deltoids"], ["Sit tall with a neutral spine.", "Pull the handle toward your torso.", "Reach forward without rounding excessively."]),
    ("Overhead Press", "shoulders", ["triceps", "upper chest"], ["Brace your trunk and glutes.", "Press the weight overhead.", "Finish with the weight balanced over mid-foot."]),
    ("Dumbbell Lateral Raise", "side deltoids", ["upper traps"], ["Keep a slight bend in your elbows.", "Raise the dumbbells to shoulder height.", "Lower slowly."]),
    ("Face Pull", "rear deltoids", ["upper back", "rotator cuff"], ["Set the cable near face height.", "Pull toward your face with elbows high.", "Return under control."]),
    ("Barbell Curl", "biceps", ["forearms"], ["Keep your upper arms still.", "Curl without swinging.", "Lower through the full range."]),
    ("Triceps Pushdown", "triceps", ["forearms"], ["Keep your elbows beside your torso.", "Extend your elbows fully.", "Return without lifting your shoulders."]),
    ("Leg Press", "quadriceps", ["glutes", "hamstrings"], ["Place your feet securely on the platform.", "Lower within a comfortable range.", "Press without locking your knees forcefully."]),
    ("Walking Lunge", "quadriceps", ["glutes", "hamstrings"], ["Step forward with control.", "Lower both knees comfortably.", "Drive through the front foot into the next step."]),
    ("Leg Curl", "hamstrings", ["calves"], ["Set the machine to align with your knee.", "Curl through a controlled range.", "Lower slowly."]),
    ("Standing Calf Raise", "calves", [], ["Stand securely on the platform.", "Rise onto the balls of your feet.", "Lower into a comfortable stretch."]),
    ("Plank", "core", ["glutes", "shoulders"], ["Brace your abdomen and glutes.", "Keep a straight body position.", "Breathe while holding tension."]),
    ("Dead Bug", "core", ["hip flexors"], ["Keep your lower back gently supported.", "Extend opposite arm and leg.", "Return without losing trunk control."]),
]


def seed_exercises():
    existing = {name for (name,) in db.session.query(Exercise.name).all()}
    additions = [
        Exercise(name=name, target=target, secondary_muscles=secondary, instructions=instructions)
        for name, target, secondary, instructions in EXERCISES
        if name not in existing
    ]
    db.session.add_all(additions)
    db.session.commit()
    return len(additions)
