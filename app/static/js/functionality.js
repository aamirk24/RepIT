function deleteWorkout(url, workoutId, button, event){
    event.stopPropagation();

    fetch('/delete_workout',{
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({workoutId: workoutId})
    }).then((_res) =>{
        window.location.href = "/";
    });
}

function deleteSession(url, sessionId, button, event){
    event.stopPropagation();

    fetch('/delete_session',{
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({sessionId: sessionId})
    }).then((_res) =>{
        window.location.href = "/";
    });
}

// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.content : getCookie('csrf_token');
}

document.addEventListener('DOMContentLoaded', function() {
    let activeWorkoutSession = null;
    let startTime = null;
    let timerInterval = null;

    const customWorkoutBtn = document.getElementById('custom-workout-btn');
    if (!customWorkoutBtn) return;
    const inactiveWorkoutDiv = document.getElementById('no-active-workout');
    const activeWorkoutDiv = document.getElementById('active-workout');
    const endWorkoutBtn = document.getElementById('end-workout-btn');
    const addExerciseBtn = document.getElementById('add-exercise-btn');
    const exerciseSearchModal = new bootstrap.Modal(document.getElementById('exerciseSearchModal'));
    const exerciseSearchInput = document.getElementById('exercise-search-input');
    const exerciseSearchResults = document.getElementById('exercise-search-results');
    const workoutExercises = document.getElementById('workout-exercises');
    const timerDisplay = document.getElementById('timer');

    function startTimer() {
        startTime = new Date();
        timerInterval = setInterval(updateTimer, 1000);
    }

    function updateTimer() {
        const currentTime = new Date();
        const diff = currentTime - startTime;
        const hours = Math.floor(diff / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        timerDisplay.textContent =
            `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }


    // Creating new set
    function createSetElement(exerciseCard, setNumber) {
        const setRow = document.createElement('div');
        setRow.classList.add('d-flex', 'align-items-center', 'mb-2', 'set-row');
        setRow.innerHTML = `
            <div class="col-2">
                <span class="me-2">Set ${setNumber}</span>
            </div>
            <div class="col-10 d-flex">
                <input type="number" class="form-control form-control-sm me-2 reps-input" placeholder="Reps" style="width: 100px;">
                <input type="number" step="2.5" min="0" class="form-control form-control-sm me-2 weight-input" placeholder="Weight (kg)" style="width: 100px;">
                <button class="btn btn-sm btn-signup save-set-btn me-2">
                    Completed
                </button>
                <button class="btn btn-sm btn-delete remove-set-btn">
                    <i class="bx bxs-trash"></i>
                </button>
            </div>
        `;

        const setsContainer = exerciseCard.querySelector('.sets-container');
        setsContainer.appendChild(setRow);

        const saveSetBtn = setRow.querySelector('.save-set-btn');
        const removeSetBtn = setRow.querySelector('.remove-set-btn');
        const repsInput = setRow.querySelector('.reps-input');
        const weightInput = setRow.querySelector('.weight-input');

        // Validating if sets are entered and adding to database
        saveSetBtn.addEventListener('click', function() {
            if (!repsInput.value) {
                alert('Please enter reps');
                return;
            }

            fetch('/add_exercise_set', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    session_id: activeWorkoutSession,
                    exercise_id: exerciseCard.dataset.exerciseId,
                    set_number: setNumber,
                    reps: repsInput.value,
                    weight: weightInput.value || null
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    repsInput.setAttribute('disabled', true);
                    weightInput.setAttribute('disabled', true);
                    saveSetBtn.classList.remove('btn-success');
                    saveSetBtn.classList.add('btn-secondary');
                    saveSetBtn.disabled = true;
                    removeSetBtn.disabled = true;
                }
            });
        });

        // Removing set
        removeSetBtn.addEventListener('click', function() {
            setsContainer.removeChild(setRow);
        });

        return setRow;
    }


    // Adding new exercise
    function createExerciseCard(exerciseId, exerciseName, gifUrl, exerciseMuscle) {
        const newExerciseCard = document.createElement('div');
        newExerciseCard.classList.add('card', 'mb-3');
        newExerciseCard.dataset.exerciseId = exerciseId;
        newExerciseCard.innerHTML = `
            <div class="card-body">
                <div class="row">
                    <div class="image col-lg-2 my-4">
                        ${gifUrl ? `<img src="${gifUrl}" alt="${exerciseName}" style="max-height:100px">` : ''}
                    </div>
                    <div class="col-lg-2 my-4">
                        <h5 class="name card-title mb-0">
                            ${exerciseName}
                        </h5>
                        <p class="target text-muted">
                            Primary Muscle:
                        </p>
                        <p class="target2 text-muted">
                            ${exerciseMuscle}
                        </p>
                    </div>

                    <div class="col-lg-8 justify-content-center">
                        <div class="text-end">
                            <button type="button" class="btn-close remove-exercise-btn mb-2"></button>
                        </div>
                        <div class="card">
                            <div class="card-body flex-column justify-content-center">
                                <div class="sets-container"></div>
                                <button class="btn btn-signup btn-sm add-set-btn mt-2">
                                   Add Set
                                </button>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        `;


        // Removing exercise
        const removeExerciseBtn = newExerciseCard.querySelector('.remove-exercise-btn');
        removeExerciseBtn.addEventListener('click', function() {
            fetch('/remove_session_exercise', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    session_id: activeWorkoutSession,
                    exercise_id: exerciseId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    workoutExercises.removeChild(newExerciseCard);
                }
            });
        });

        const addSetBtn = newExerciseCard.querySelector('.add-set-btn');
        const setsContainer = newExerciseCard.querySelector('.sets-container');

        addSetBtn.addEventListener('click', function() {
            const currentSetCount = setsContainer.children.length;
            createSetElement(newExerciseCard, currentSetCount + 1);
        });

        return newExerciseCard;
    }


    // Event Listeners
    addExerciseBtn.addEventListener('click', function() {
        exerciseSearchModal.show();
    });

    exerciseSearchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const exerciseItems = document.querySelectorAll('.exercise-search-item');

        exerciseItems.forEach(item => {
            const exerciseName = item.querySelector('.card-title').textContent.toLowerCase();
            item.style.display = exerciseName.includes(searchTerm) ? 'block' : 'none';
        });
    });

    exerciseSearchResults.addEventListener('click', function(event) {
        const selectButton = event.target.closest('.select-exercise-btn');
        if (selectButton) {
            const exerciseCard = selectButton.closest('.exercise-search-item');
            const exerciseId = exerciseCard.dataset.exerciseId;
            const exerciseName = exerciseCard.dataset.exerciseName;
            const gifUrl = exerciseCard.dataset.exerciseGifUrl;
            const exerciseMuscle = exerciseCard.dataset.exerciseTarget;

            // Create exercise card in active workout
            const newExerciseCard = createExerciseCard(exerciseId, exerciseName, gifUrl, exerciseMuscle);
            workoutExercises.appendChild(newExerciseCard);

            // Send exercise to server
            fetch('/add_session_exercise', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    session_id: activeWorkoutSession,
                    exercise_id: exerciseId
                })
            });

            exerciseSearchModal.hide();
        }
    });

    // Start workout functions
    function startWorkout(workoutId = null) {
        fetch('/start_empty_workout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(workoutId ? { workout_id: workoutId } : {})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                activeWorkoutSession = data.session_id;
                inactiveWorkoutDiv.classList.add('d-none');
                activeWorkoutDiv.classList.remove('d-none');
                startTimer();
                (data.exercises || []).forEach(exercise => {
                    workoutExercises.appendChild(createExerciseCard(exercise.id, exercise.name, exercise.gifUrl || '', exercise.target));
                });
            }
        });
    }

    customWorkoutBtn.addEventListener('click', function() {
        startWorkout();
    });

    const initialRoutineId = document.getElementById('tracking-app').dataset.routineId;
    if (initialRoutineId) startWorkout(Number(initialRoutineId));

    const discardWorkoutBtn = document.getElementById('discard-workout-btn');

    // Discard workout functionality
    discardWorkoutBtn.addEventListener('click', function () {

        inactiveWorkoutDiv.classList.remove('d-none');
        activeWorkoutDiv.classList.add('d-none');
        workoutExercises.innerHTML = ''; // Clear the exercises
        timerDisplay.textContent = '00:00:00'; // Reset timer

        fetch('/discard_workout_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ session_id: activeWorkoutSession })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log("Workout session discarded successfully.");
                activeWorkoutSession = null;
            } else {
                console.error("Failed to discard workout session.");
            }
        });
    });

   const workoutNameModal = new bootstrap.Modal(document.getElementById('workoutNameModal'), {
        backdrop: 'static',
        keyboard: false
    });
    const workoutNameInput = document.getElementById('workout-name-input');
    const submitWorkoutNameBtn = document.getElementById('submit-workout-name-btn');

    endWorkoutBtn.addEventListener('click', function() {
        console.log('End workout button clicked');
        clearInterval(timerInterval);

        // Collect all exercises and their sets
        const sessionExercises = Array.from(workoutExercises.children).map(exerciseCard => {
            const exerciseId = exerciseCard.dataset.exerciseId;
            const exerciseName = exerciseCard.querySelector('.card-title').textContent;
            const sets = Array.from(exerciseCard.querySelectorAll('.set-row')).map(setRow => {
                const repsInput = setRow.querySelector('.reps-input');
                const weightInput = setRow.querySelector('.weight-input');
                return {
                    exerciseId: exerciseId,
                    exerciseName: exerciseName,
                    reps: repsInput ? repsInput.value : null,
                    weight: weightInput ? weightInput.value : null
                };
            });
            return { exerciseId, exerciseName, sets };
        });

        console.log('Session exercises:', sessionExercises);

        // Reset input and show modal
        workoutNameInput.value = 'Custom Workout';
        workoutNameModal.show();

        // Ensure previous event listeners are removed to prevent multiple submissions
        submitWorkoutNameBtn.removeEventListener('click', handleWorkoutNameSubmission);
        submitWorkoutNameBtn.addEventListener('click', handleWorkoutNameSubmission);

        function handleWorkoutNameSubmission() {
            console.log('Submit workout name button clicked');
            const workoutName = workoutNameInput.value.trim();
            console.log('Workout name:', workoutName);
            console.log('Active workout session:', activeWorkoutSession);

            // End the workout session
            fetch('/end_workout_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    session_id: activeWorkoutSession,
                    exercises: sessionExercises,
                    duration: timerDisplay.textContent,
                    workout_name: workoutName
                })
            })
            .then(response => {
                console.log('Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Server response:', data);
                if (data.success || data.status === 'success') {
                    inactiveWorkoutDiv.classList.remove('d-none');
                    activeWorkoutDiv.classList.add('d-none');
                    workoutExercises.innerHTML = ''; // Clear exercises

                    // Reset workout select and timer
                    timerDisplay.textContent = '00:00:00';
                    activeWorkoutSession = null;

                    workoutNameModal.hide();
                    window.location.href = '/tracking';
                } else {
                    console.error('Failed to end workout session');
                    alert('Failed to save workout. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error ending workout session:', error);
                alert('An error occurred. Please try again.');
            });
        }
    });
});


document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('exerciseSearch');

    // Only add the event listener if the searchInput element exists
    if (searchInput) {
        const exerciseGrid = document.getElementById('exerciseGrid');
        const exerciseCards = document.querySelectorAll('.exercise-card');
        const exerciseCount = document.getElementById('exerciseCount');
        const totalExercises = exerciseCards.length;

        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase().trim();
            let visibleCount = 0;

            exerciseCards.forEach(card => {
                const name = card.dataset.name;
                const target = card.dataset.target
                // Check if search term matches name, target, or secondary muscles
                const isVisible = !searchTerm ||
                    name.includes(searchTerm) ||
                    target.includes(searchTerm)

                card.style.display = isVisible ? 'block' : 'none';

                if (isVisible) visibleCount++;
            });

            // Update exercise count
            exerciseCount.textContent = `${visibleCount} of ${totalExercises}`;
        });
    }
});
