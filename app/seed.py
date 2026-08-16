from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from . import db
from .models import Exercise


CATALOG_VERSION = "2026.08.1"
CATALOG_SOURCE = "RepIT"


@dataclass(frozen=True)
class CatalogSeedResult:
    created: int
    updated: int


class ExerciseCatalogProvider(Protocol):
    """Maps any licensed exercise source into RepIT's normalized catalogue."""

    source: str

    def records(self) -> Iterable[dict]: ...


class BundledExerciseCatalogProvider:
    """Temporary offline provider used until an external provider is approved."""

    source = CATALOG_SOURCE

    def records(self):
        return EXERCISES


def exercise(slug, name, body_part, target, equipment, difficulty, category, secondary, description, instructions):
    return {
        "slug": slug,
        "name": name,
        "body_part": body_part,
        "target": target,
        "equipment": equipment,
        "difficulty": difficulty,
        "category": category,
        "secondary_muscles": secondary,
        "description": description,
        "instructions": instructions,
        "source": CATALOG_SOURCE,
        "source_identifier": slug,
        "source_url": None,
        "license_name": None,
        "license_url": None,
        "attribution_text": "Temporary bundled exercise guidance for RepIT development.",
        "catalog_version": CATALOG_VERSION,
        "is_active": True,
    }


EXERCISES = [
    exercise("barbell-back-squat", "Barbell Back Squat", "lower body", "quadriceps", "barbell", "intermediate", "strength", ["glutes", "hamstrings"], "A compound lower-body movement for developing leg and trunk strength.", ["Set the bar securely across your upper back.", "Brace your trunk and sit down between your hips.", "Drive through your feet to stand tall."]),
    exercise("romanian-deadlift", "Romanian Deadlift", "lower body", "hamstrings", "barbell", "intermediate", "strength", ["glutes", "lower back"], "A hip-hinge movement that emphasises the hamstrings and glutes.", ["Hold the bar close to your thighs.", "Push your hips back with a neutral spine.", "Stand by driving your hips forward."]),
    exercise("conventional-deadlift", "Conventional Deadlift", "full body", "posterior chain", "barbell", "advanced", "strength", ["glutes", "hamstrings", "back"], "A compound pull that trains force production across the posterior chain.", ["Stand with the bar over mid-foot.", "Brace and push the floor away.", "Finish tall without leaning back."]),
    exercise("barbell-bench-press", "Barbell Bench Press", "upper body", "chest", "barbell", "intermediate", "strength", ["triceps", "front deltoids"], "A horizontal press for chest, triceps and shoulder strength.", ["Set your shoulder blades against the bench.", "Lower the bar under control.", "Press until your arms are straight."]),
    exercise("incline-dumbbell-press", "Incline Dumbbell Press", "upper body", "upper chest", "dumbbells", "intermediate", "strength", ["triceps", "front deltoids"], "An angled dumbbell press that places additional emphasis on the upper chest.", ["Set the bench to a low incline.", "Lower the dumbbells beside your upper chest.", "Press while keeping your shoulders stable."]),
    exercise("push-up", "Push-Up", "upper body", "chest", "bodyweight", "beginner", "strength", ["triceps", "core"], "A bodyweight horizontal press that also develops trunk control.", ["Keep a straight line from head to heel.", "Lower your chest with control.", "Push the floor away."]),
    exercise("pull-up", "Pull-Up", "upper body", "back", "pull-up bar", "intermediate", "strength", ["biceps", "forearms"], "A vertical bodyweight pull for back and arm strength.", ["Start from a controlled hang.", "Pull your elbows toward your sides.", "Lower without dropping."]),
    exercise("lat-pulldown", "Lat Pulldown", "upper body", "back", "cable machine", "beginner", "strength", ["biceps", "rear deltoids"], "A cable-based vertical pull that develops the back through a controllable range.", ["Brace your torso.", "Pull the bar toward your upper chest.", "Return to full reach with control."]),
    exercise("seated-cable-row", "Seated Cable Row", "upper body", "back", "cable machine", "beginner", "strength", ["biceps", "rear deltoids"], "A supported horizontal pull for the back and arms.", ["Sit tall with a neutral spine.", "Pull the handle toward your torso.", "Reach forward without excessive rounding."]),
    exercise("overhead-press", "Overhead Press", "upper body", "shoulders", "barbell", "intermediate", "strength", ["triceps", "upper chest"], "A standing vertical press for shoulder strength and whole-body stability.", ["Brace your trunk and glutes.", "Press the weight overhead.", "Finish with the weight balanced over mid-foot."]),
    exercise("dumbbell-lateral-raise", "Dumbbell Lateral Raise", "upper body", "side deltoids", "dumbbells", "beginner", "strength", ["upper traps"], "An isolation movement for the lateral shoulder muscles.", ["Keep a slight bend in your elbows.", "Raise the dumbbells to shoulder height.", "Lower slowly."]),
    exercise("face-pull", "Face Pull", "upper body", "rear deltoids", "cable machine", "beginner", "strength", ["upper back", "rotator cuff"], "A cable pull supporting rear-shoulder and upper-back development.", ["Set the cable near face height.", "Pull toward your face with elbows high.", "Return under control."]),
    exercise("barbell-curl", "Barbell Curl", "upper body", "biceps", "barbell", "beginner", "strength", ["forearms"], "An elbow-flexion exercise for the biceps and forearms.", ["Keep your upper arms still.", "Curl without swinging.", "Lower through the full range."]),
    exercise("triceps-pushdown", "Triceps Pushdown", "upper body", "triceps", "cable machine", "beginner", "strength", ["forearms"], "A cable isolation movement for the triceps.", ["Keep your elbows beside your torso.", "Extend your elbows fully.", "Return without lifting your shoulders."]),
    exercise("leg-press", "Leg Press", "lower body", "quadriceps", "machine", "beginner", "strength", ["glutes", "hamstrings"], "A machine-based compound leg exercise with external support.", ["Place your feet securely on the platform.", "Lower within a comfortable range.", "Press without forcefully locking your knees."]),
    exercise("walking-lunge", "Walking Lunge", "lower body", "quadriceps", "bodyweight", "intermediate", "strength", ["glutes", "hamstrings"], "A unilateral lower-body movement that also challenges balance.", ["Step forward with control.", "Lower both knees comfortably.", "Drive through the front foot into the next step."]),
    exercise("leg-curl", "Leg Curl", "lower body", "hamstrings", "machine", "beginner", "strength", ["calves"], "A machine isolation movement for knee-flexion strength.", ["Align the machine with your knee joint.", "Curl through a controlled range.", "Lower slowly."]),
    exercise("standing-calf-raise", "Standing Calf Raise", "lower body", "calves", "bodyweight", "beginner", "strength", [], "An ankle-extension movement for the calf muscles.", ["Stand securely on the platform.", "Rise onto the balls of your feet.", "Lower into a comfortable stretch."]),
    exercise("plank", "Plank", "core", "core", "bodyweight", "beginner", "stability", ["glutes", "shoulders"], "An isometric trunk exercise for maintaining a stable body position.", ["Brace your abdomen and glutes.", "Keep a straight body position.", "Breathe while holding tension."]),
    exercise("dead-bug", "Dead Bug", "core", "core", "bodyweight", "beginner", "stability", ["hip flexors"], "A controlled trunk exercise that coordinates opposite arm and leg movement.", ["Keep your lower back gently supported.", "Extend the opposite arm and leg.", "Return without losing trunk control."]),
    exercise("goblet-squat", "Goblet Squat", "lower body", "quadriceps", "dumbbell", "beginner", "strength", ["glutes", "core"], "A front-loaded squat that helps develop lower-body strength and squat control.", ["Hold one dumbbell close to your chest.", "Sit down between your hips while keeping your chest tall.", "Drive through your feet to stand."]),
    exercise("barbell-front-squat", "Barbell Front Squat", "lower body", "quadriceps", "barbell", "advanced", "strength", ["glutes", "upper back"], "A front-loaded barbell squat requiring leg strength and upper-body position control.", ["Support the bar across the front of your shoulders.", "Keep your elbows lifted as you descend.", "Stand while maintaining an upright torso."]),
    exercise("bulgarian-split-squat", "Bulgarian Split Squat", "lower body", "quadriceps", "dumbbells", "intermediate", "strength", ["glutes", "hamstrings"], "A rear-foot-elevated unilateral squat for leg strength and balance.", ["Place the rear foot on a stable bench.", "Lower the back knee while controlling the front leg.", "Drive through the front foot to rise."]),
    exercise("barbell-hip-thrust", "Barbell Hip Thrust", "lower body", "glutes", "barbell", "intermediate", "strength", ["hamstrings", "core"], "A loaded hip-extension movement focused on the glutes.", ["Support your upper back on a stable bench.", "Drive your hips upward while keeping your trunk braced.", "Lower the bar under control."]),
    exercise("glute-bridge", "Glute Bridge", "lower body", "glutes", "bodyweight", "beginner", "strength", ["hamstrings", "core"], "A floor-based hip-extension exercise suitable for learning glute control.", ["Lie down with your knees bent and feet planted.", "Lift your hips by squeezing your glutes.", "Lower without losing control."]),
    exercise("dumbbell-step-up", "Dumbbell Step-Up", "lower body", "quadriceps", "dumbbells", "intermediate", "strength", ["glutes", "hamstrings"], "A unilateral stepping movement for leg strength and coordination.", ["Place one foot fully on a stable platform.", "Drive through the raised foot to stand on the platform.", "Step down slowly and repeat."]),
    exercise("leg-extension", "Leg Extension", "lower body", "quadriceps", "machine", "beginner", "strength", [], "A machine isolation movement for the quadriceps.", ["Align your knee with the machine pivot.", "Extend your knees through a comfortable range.", "Lower the pad slowly."]),
    exercise("seated-calf-raise", "Seated Calf Raise", "lower body", "calves", "machine", "beginner", "strength", [], "A seated ankle-extension movement that trains the calf muscles.", ["Position the pad securely above your knees.", "Raise your heels as high as comfortable.", "Lower into a controlled stretch."]),
    exercise("dumbbell-bench-press", "Dumbbell Bench Press", "upper body", "chest", "dumbbells", "beginner", "strength", ["triceps", "front deltoids"], "A horizontal dumbbell press allowing each arm to move independently.", ["Set your shoulders firmly against the bench.", "Lower the dumbbells beside your chest.", "Press upward without allowing the weights to collide."]),
    exercise("cable-chest-fly", "Cable Chest Fly", "upper body", "chest", "cable machine", "intermediate", "strength", ["front deltoids"], "A cable movement that trains the chest through horizontal arm adduction.", ["Stand between the cables with a stable stance.", "Bring your hands together with softly bent elbows.", "Return until you feel a comfortable chest stretch."]),
    exercise("parallel-bar-dip", "Parallel Bar Dip", "upper body", "triceps", "parallel bars", "advanced", "strength", ["chest", "front deltoids"], "A bodyweight pressing movement for the triceps, chest and shoulders.", ["Support yourself with straight arms.", "Lower while keeping your shoulders controlled.", "Press back to the starting position."]),
    exercise("chest-supported-dumbbell-row", "Chest-Supported Dumbbell Row", "upper body", "back", "dumbbells", "beginner", "strength", ["biceps", "rear deltoids"], "A supported horizontal pull that reduces the need for lower-back stabilisation.", ["Lie chest-down on an inclined bench.", "Pull the dumbbells toward your sides.", "Lower until your arms are extended."]),
    exercise("one-arm-dumbbell-row", "One-Arm Dumbbell Row", "upper body", "back", "dumbbell", "intermediate", "strength", ["biceps", "rear deltoids"], "A unilateral horizontal pull for back and arm strength.", ["Support yourself with the opposite hand.", "Pull the dumbbell toward your hip.", "Lower while keeping your torso steady."]),
    exercise("assisted-pull-up", "Assisted Pull-Up", "upper body", "back", "machine", "beginner", "strength", ["biceps", "forearms"], "A supported vertical pull that develops strength toward an unassisted pull-up.", ["Select enough assistance to control the movement.", "Pull your elbows toward your sides.", "Return to a full reach without dropping."]),
    exercise("arnold-press", "Arnold Press", "upper body", "shoulders", "dumbbells", "intermediate", "strength", ["triceps", "front deltoids"], "A rotating dumbbell press that trains the shoulders through a long range.", ["Begin with the dumbbells in front of your shoulders.", "Rotate your palms outward as you press.", "Reverse the movement under control."]),
    exercise("reverse-dumbbell-fly", "Reverse Dumbbell Fly", "upper body", "rear deltoids", "dumbbells", "beginner", "strength", ["upper back"], "An isolation movement for the rear shoulders and upper back.", ["Hinge forward with a supported neutral spine.", "Raise the dumbbells out to the sides.", "Lower slowly without swinging."]),
    exercise("hammer-curl", "Hammer Curl", "upper body", "biceps", "dumbbells", "beginner", "strength", ["forearms"], "A neutral-grip curl for the arms and forearms.", ["Hold the dumbbells with palms facing inward.", "Curl while keeping your upper arms still.", "Lower through the full range."]),
    exercise("incline-dumbbell-curl", "Incline Dumbbell Curl", "upper body", "biceps", "dumbbells", "intermediate", "strength", ["forearms"], "A seated curl performed with the arms slightly behind the torso.", ["Sit against a moderately inclined bench.", "Curl without moving your upper arms forward.", "Lower the dumbbells slowly."]),
    exercise("overhead-triceps-extension", "Overhead Triceps Extension", "upper body", "triceps", "dumbbell", "beginner", "strength", [], "An overhead elbow-extension exercise for the triceps.", ["Hold the dumbbell securely above your head.", "Bend your elbows to lower the weight behind you.", "Extend your elbows without flaring excessively."]),
    exercise("hanging-knee-raise", "Hanging Knee Raise", "core", "abdominals", "pull-up bar", "intermediate", "strength", ["hip flexors", "forearms"], "A hanging trunk exercise combining abdominal control and grip strength.", ["Begin in a stable hang.", "Raise your knees without swinging.", "Lower slowly to the starting position."]),
    exercise("bird-dog", "Bird Dog", "core", "core", "bodyweight", "beginner", "stability", ["glutes", "shoulders"], "A quadruped stability exercise coordinating opposite arm and leg movement.", ["Begin on your hands and knees.", "Extend the opposite arm and leg while keeping your hips level.", "Return and alternate sides."]),
    exercise("side-plank", "Side Plank", "core", "obliques", "bodyweight", "intermediate", "stability", ["glutes", "shoulders"], "An isometric side-body exercise for lateral trunk stability.", ["Support yourself on one forearm and the side of your foot.", "Lift your hips into a straight body line.", "Hold while breathing normally."]),
    exercise("cable-crunch", "Cable Crunch", "core", "abdominals", "cable machine", "intermediate", "strength", [], "A kneeling cable exercise for loaded trunk flexion.", ["Kneel while holding the cable near your head.", "Curl your ribcage toward your pelvis.", "Return without pulling primarily with your arms."]),
    exercise("kettlebell-swing", "Kettlebell Swing", "full body", "posterior chain", "kettlebell", "intermediate", "strength", ["glutes", "hamstrings", "core"], "A dynamic hip-hinge movement that develops repeated power and conditioning.", ["Hike the kettlebell back between your legs.", "Drive your hips forward to project the bell.", "Guide it back into the next hinge without squatting deeply."]),
    exercise("battle-rope-waves", "Battle Rope Waves", "full body", "conditioning", "battle ropes", "beginner", "cardio", ["shoulders", "core"], "A low-impact conditioning drill using repeated rope waves.", ["Stand in an athletic position with one rope end in each hand.", "Create alternating waves while keeping your trunk braced.", "Maintain a sustainable rhythm for the interval."]),
    exercise("rowing-machine", "Rowing Machine", "full body", "conditioning", "rowing machine", "beginner", "cardio", ["legs", "back", "arms"], "A cyclical conditioning movement combining leg drive and upper-body pulling.", ["Begin each stroke by driving through your legs.", "Lean back slightly and draw the handle toward your lower ribs.", "Return the arms, body and legs in sequence."]),
    exercise("incline-treadmill-walk", "Incline Treadmill Walk", "lower body", "conditioning", "treadmill", "beginner", "cardio", ["calves", "glutes"], "A controllable walking exercise for aerobic conditioning.", ["Choose a speed and incline you can sustain safely.", "Walk tall without leaning heavily on the rails.", "Reduce the incline and speed gradually when finishing."]),
    exercise("stationary-bike", "Stationary Bike", "lower body", "conditioning", "stationary bike", "beginner", "cardio", ["quadriceps", "glutes"], "A seated cyclical exercise for aerobic conditioning.", ["Adjust the seat so your knee remains slightly bent at the bottom.", "Pedal at a smooth sustainable cadence.", "Lower the resistance gradually before stopping."]),
    exercise("cat-cow", "Cat-Cow", "spine", "spinal mobility", "bodyweight", "beginner", "mobility", ["core"], "A gentle quadruped movement exploring spinal flexion and extension.", ["Begin on your hands and knees.", "Move gradually between a rounded and extended spine.", "Stay within a comfortable range and breathe continuously."]),
    exercise("half-kneeling-hip-flexor-stretch", "Half-Kneeling Hip Flexor Stretch", "lower body", "hip flexors", "bodyweight", "beginner", "stretching", ["quadriceps"], "A half-kneeling position used to stretch the front of the hip.", ["Kneel on one knee with the other foot forward.", "Tuck your pelvis slightly and shift forward.", "Hold a comfortable stretch without arching your lower back."]),
    exercise("open-book-rotation", "Open Book Rotation", "upper body", "thoracic mobility", "bodyweight", "beginner", "mobility", ["chest", "shoulders"], "A side-lying rotation for upper-spine and shoulder mobility.", ["Lie on your side with hips and knees bent.", "Rotate the top arm and upper back away from your knees.", "Return slowly while keeping the knees together."]),
    exercise("ankle-rock", "Ankle Rock", "lower body", "ankle mobility", "bodyweight", "beginner", "mobility", ["calves"], "A controlled drill for exploring ankle dorsiflexion.", ["Stand facing a wall with one foot forward.", "Guide the front knee toward the wall without lifting the heel.", "Move in and out of the comfortable range."]),
]


def seed_exercises(provider: ExerciseCatalogProvider | None = None):
    provider = provider or BundledExerciseCatalogProvider()
    existing = {
        (item.source, item.source_identifier): item
        for item in db.session.scalars(db.select(Exercise)).all()
        if item.source_identifier
    }
    created = 0
    updated = 0
    for data in provider.records():
        if data["source"] != provider.source:
            raise ValueError("Catalogue record source does not match its provider.")
        key = (data["source"], data["source_identifier"])
        record = existing.get(key)
        if record is None:
            db.session.add(Exercise(**data))
            created += 1
            continue
        changed = False
        for field, value in data.items():
            if getattr(record, field) != value:
                setattr(record, field, value)
                changed = True
        if changed:
            updated += 1
    db.session.commit()
    return CatalogSeedResult(created=created, updated=updated)
