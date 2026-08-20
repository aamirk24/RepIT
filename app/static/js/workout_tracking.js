document.addEventListener('DOMContentLoaded', () => {
    const app = document.getElementById('tracking-app');
    if (!app) return;

    const initialState = JSON.parse(document.getElementById('active-workout-data').textContent);
    const inactivePanel = document.getElementById('no-active-workout');
    const activePanel = document.getElementById('active-workout');
    const exercisesContainer = document.getElementById('workout-exercises');
    const timer = document.getElementById('timer');
    const nameInput = document.getElementById('active-workout-name');
    const notesInput = document.getElementById('active-workout-notes');
    const status = document.getElementById('workout-status');
    const searchModal = new bootstrap.Modal(document.getElementById('exerciseSearchModal'));
    let session = initialState;
    let timerHandle = null;

    const request = async (url, body) => {
        const response = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
            body: JSON.stringify(body)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || 'The workout could not be updated.');
        return data;
    };

    const showStatus = (message, isError = false) => {
        status.textContent = message;
        status.className = isError ? 'small text-danger mt-2' : 'small text-success mt-2';
    };

    const updateTimer = () => {
        if (!session) return;
        const elapsed = Math.max(0, Date.now() - new Date(session.startTime).getTime());
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        timer.textContent = [hours, minutes, seconds].map(value => String(value).padStart(2, '0')).join(':');
    };

    const startTimer = () => {
        window.clearInterval(timerHandle);
        updateTimer();
        timerHandle = window.setInterval(updateTimer, 1000);
    };

    const renumberSets = card => {
        card.querySelectorAll('.set-row').forEach((row, index) => {
            row.dataset.setNumber = index + 1;
            row.querySelector('.set-label').textContent = `Set ${index + 1}`;
        });
    };

    const createSetRow = (card, set = {}) => {
        const row = document.createElement('div');
        row.className = 'row g-2 align-items-center mb-2 set-row';
        row.dataset.setNumber = set.setNumber || card.querySelectorAll('.set-row').length + 1;
        row.dataset.persisted = set.id ? 'true' : 'false';
        row.dataset.dirty = set.id ? 'false' : 'true';
        row.innerHTML = `
            <div class="col-12 col-sm-2 set-label"></div>
            <div class="col-4 col-sm-2"><input type="number" min="1" class="form-control form-control-sm reps-input" aria-label="Repetitions" placeholder="Reps"></div>
            <div class="col-4 col-sm-3"><input type="number" min="0" step="0.25" class="form-control form-control-sm weight-input" aria-label="Weight in kilograms" placeholder="Weight kg"></div>
            <div class="col-4 col-sm-2"><input type="number" min="0" class="form-control form-control-sm rest-input" aria-label="Rest in seconds" placeholder="Rest sec"></div>
            <div class="col-12 col-sm-3 d-flex gap-2"><button type="button" class="btn btn-sm btn-signup save-set-btn">Save</button><button type="button" class="btn btn-sm btn-delete remove-set-btn">Remove</button></div>`;
        row.querySelector('.reps-input').value = set.reps ?? '';
        row.querySelector('.weight-input').value = set.weight ?? '';
        row.querySelector('.rest-input').value = set.restTime ?? '';
        row.querySelector('.set-label').textContent = `Set ${row.dataset.setNumber}`;
        row.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', () => { row.dataset.dirty = 'true'; });
        });

        row.querySelector('.save-set-btn').addEventListener('click', async () => {
            try {
                const data = await request('/add_exercise_set', {
                    session_id: session.id,
                    exercise_id: card.dataset.exerciseId,
                    set_number: row.dataset.setNumber,
                    reps: row.querySelector('.reps-input').value,
                    weight: row.querySelector('.weight-input').value,
                    rest_time: row.querySelector('.rest-input').value
                });
                row.dataset.persisted = 'true';
                row.dataset.dirty = 'false';
                row.dataset.setId = data.set_id;
                showStatus('Set saved.');
            } catch (error) {
                showStatus(error.message, true);
            }
        });

        row.querySelector('.remove-set-btn').addEventListener('click', async () => {
            try {
                if (row.dataset.persisted === 'true') {
                    await request('/delete_exercise_set', {
                        session_id: session.id,
                        exercise_id: card.dataset.exerciseId,
                        set_number: row.dataset.setNumber
                    });
                }
                row.remove();
                renumberSets(card);
                showStatus('Set removed.');
            } catch (error) {
                showStatus(error.message, true);
            }
        });
        return row;
    };

    const persistOrder = async () => {
        const exerciseIds = [...exercisesContainer.children].map(card => Number(card.dataset.exerciseId));
        await request('/reorder_session_exercises', {session_id: session.id, exercise_ids: exerciseIds});
    };

    const createExerciseCard = exercise => {
        const card = document.createElement('article');
        card.className = 'card mb-3 workout-exercise-card';
        card.dataset.exerciseId = exercise.id;
        card.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between gap-3 mb-3">
                    <div class="d-flex gap-3 align-items-center exercise-summary"></div>
                    <div class="d-flex gap-1 align-items-start">
                        <button type="button" class="btn btn-sm btn-outline-secondary move-up-btn" aria-label="Move exercise up">↑</button>
                        <button type="button" class="btn btn-sm btn-outline-secondary move-down-btn" aria-label="Move exercise down">↓</button>
                        <button type="button" class="btn btn-sm btn-delete remove-exercise-btn">Remove</button>
                    </div>
                </div>
                <div class="sets-container"></div>
                <button type="button" class="btn btn-signup btn-sm add-set-btn mt-2">Add Set</button>
            </div>`;
        const summary = card.querySelector('.exercise-summary');
        if (exercise.imageUrl) {
            const image = document.createElement('img');
            image.src = exercise.imageUrl;
            image.alt = '';
            image.loading = 'lazy';
            summary.appendChild(image);
        }
        const text = document.createElement('div');
        const heading = document.createElement('h5');
        heading.className = 'card-title mb-1';
        heading.textContent = exercise.name;
        const detail = document.createElement('p');
        detail.className = 'text-muted mb-0';
        detail.textContent = `${exercise.target} · ${exercise.equipment || 'No equipment'}`;
        text.append(heading, detail);
        summary.appendChild(text);

        const setsContainer = card.querySelector('.sets-container');
        (exercise.sets || []).forEach(set => setsContainer.appendChild(createSetRow(card, set)));
        card.querySelector('.add-set-btn').addEventListener('click', () => setsContainer.appendChild(createSetRow(card)));
        card.querySelector('.remove-exercise-btn').addEventListener('click', async () => {
            if (!window.confirm(`Remove ${exercise.name} and its logged sets?`)) return;
            try {
                await request('/remove_session_exercise', {session_id: session.id, exercise_id: exercise.id});
                card.remove();
                showStatus('Exercise removed.');
            } catch (error) { showStatus(error.message, true); }
        });
        card.querySelector('.move-up-btn').addEventListener('click', async () => {
            if (card.previousElementSibling) {
                exercisesContainer.insertBefore(card, card.previousElementSibling);
                try { await persistOrder(); } catch (error) { showStatus(error.message, true); }
            }
        });
        card.querySelector('.move-down-btn').addEventListener('click', async () => {
            if (card.nextElementSibling) {
                exercisesContainer.insertBefore(card.nextElementSibling, card);
                try { await persistOrder(); } catch (error) { showStatus(error.message, true); }
            }
        });
        return card;
    };

    const renderSession = value => {
        session = value;
        exercisesContainer.innerHTML = '';
        inactivePanel.classList.toggle('d-none', Boolean(session));
        activePanel.classList.toggle('d-none', !session);
        if (!session) return;
        nameInput.value = session.name;
        notesInput.value = session.notes;
        session.exercises.forEach(exercise => exercisesContainer.appendChild(createExerciseCard(exercise)));
        startTimer();
    };

    const startWorkout = async routineId => {
        try {
            const data = await request('/start_empty_workout', routineId ? {workout_id: routineId} : {});
            renderSession(data.session);
            showStatus(data.created ? 'Workout started.' : 'Your active workout was restored.');
        } catch (error) { showStatus(error.message, true); }
    };

    document.getElementById('custom-workout-btn').addEventListener('click', () => startWorkout());
    document.querySelectorAll('.start-routine-btn').forEach(button => {
        button.addEventListener('click', () => startWorkout(Number(button.dataset.routineId)));
    });
    document.getElementById('add-exercise-btn').addEventListener('click', () => searchModal.show());
    document.getElementById('exercise-search-input').addEventListener('input', event => {
        const term = event.target.value.toLowerCase();
        document.querySelectorAll('.exercise-search-item').forEach(item => {
            item.style.display = item.dataset.exerciseName.toLowerCase().includes(term) ? '' : 'none';
        });
    });
    document.getElementById('exercise-search-results').addEventListener('click', async event => {
        const button = event.target.closest('.select-exercise-btn');
        if (!button) return;
        const item = button.closest('.exercise-search-item');
        try {
            const data = await request('/add_session_exercise', {session_id: session.id, exercise_id: item.dataset.exerciseId});
            exercisesContainer.appendChild(createExerciseCard(data.exercise));
            searchModal.hide();
            showStatus('Exercise added.');
        } catch (error) { showStatus(error.message, true); }
    });
    document.getElementById('save-workout-draft-btn').addEventListener('click', async () => {
        try {
            await request('/update_workout_session', {session_id: session.id, name: nameInput.value, notes: notesInput.value});
            session.name = nameInput.value.trim();
            session.notes = notesInput.value.trim();
            showStatus('Workout details saved.');
        } catch (error) { showStatus(error.message, true); }
    });
    document.getElementById('end-workout-btn').addEventListener('click', async () => {
        if (exercisesContainer.querySelector('.set-row[data-dirty="true"]')) {
            showStatus('Save or remove every edited set before finishing the workout.', true);
            return;
        }
        try {
            await request('/end_workout_session', {session_id: session.id, workout_name: nameInput.value, notes: notesInput.value});
            window.clearInterval(timerHandle);
            window.location.reload();
        } catch (error) { showStatus(error.message, true); }
    });
    document.getElementById('discard-workout-btn').addEventListener('click', async () => {
        if (!window.confirm('Discard this workout and all sets logged in it?')) return;
        try {
            await request('/discard_workout_session', {session_id: session.id});
            window.clearInterval(timerHandle);
            renderSession(null);
            showStatus('Workout discarded.');
        } catch (error) { showStatus(error.message, true); }
    });

    renderSession(session);
    const requestedRoutineId = Number(app.dataset.routineId || 0);
    if (!session && requestedRoutineId) startWorkout(requestedRoutineId);
});
