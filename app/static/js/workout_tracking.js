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
    const modalElement = document.getElementById('exerciseSearchModal');
    const searchModal = new bootstrap.Modal(modalElement);
    const searchResults = document.getElementById('exercise-search-results');
    const searchInput = document.getElementById('exercise-search-input');
    const loadMore = document.getElementById('tracking-load-more');
    const preferredWeightUnit = app.dataset.weightUnit;
    let session = initialState;
    let timerHandle = null;
    let searchPage = 1;
    let searchDebounce;
    const titleCase = value => String(value || '').replace(/\b\w/g, letter => letter.toUpperCase());

    const safeMediaUrl = value => {
        if (!value) return '';
        try {
            const url = new URL(value, window.location.origin);
            return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
        } catch { return ''; }
    };

    const request = async (url, body) => {
        const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()}, body: JSON.stringify(body)});
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || 'The workout could not be updated.');
        return data;
    };
    const showStatus = (message, isError = false) => {
        status.textContent = message;
        status.className = `small mb-0 ${isError ? 'text-warning' : 'text-white'}`;
    };
    const updateTimer = () => {
        if (!session) return;
        const elapsed = Math.max(0, Date.now() - new Date(session.startTime).getTime());
        timer.textContent = [Math.floor(elapsed / 3600000), Math.floor((elapsed % 3600000) / 60000), Math.floor((elapsed % 60000) / 1000)].map(value => String(value).padStart(2, '0')).join(':');
    };
    const startTimer = () => { window.clearInterval(timerHandle); updateTimer(); timerHandle = window.setInterval(updateTimer, 1000); };
    const mediaMarkup = exercise => {
        const frames = exercise.imageUrls || [];
        const first = safeMediaUrl(frames[0] || exercise.imageUrl || exercise.gifUrl);
        if (!first) return '<div class="active-exercise-media"></div>';
        const second = safeMediaUrl(frames[1]);
        return `<div class="active-exercise-media"><img class="exercise-demo-image" src="${first}" data-frame-one="${first}" ${second ? `data-frame-two="${second}"` : ''} data-frame-index="0" alt="" loading="lazy"></div>`;
    };

    const renumberSets = card => card.querySelectorAll('.set-row').forEach((row, index) => {
        row.dataset.setNumber = index + 1;
        row.querySelector('.set-number').textContent = index + 1;
    });
    const createSetRow = (card, set = {}) => {
        const row = document.createElement('div');
        row.className = 'set-grid set-row';
        row.dataset.setNumber = set.setNumber || card.querySelectorAll('.set-row').length + 1;
        row.dataset.persisted = set.id ? 'true' : 'false';
        row.dataset.dirty = set.id ? 'false' : 'true';
        row.innerHTML = `<span class="set-number"></span><div><label class="visually-hidden">Repetitions</label><input type="number" min="1" class="form-control form-control-sm reps-input" placeholder="Reps"></div><div><label class="visually-hidden">Weight in ${preferredWeightUnit}</label><input type="number" min="0" step="0.25" class="form-control form-control-sm weight-input" placeholder="${preferredWeightUnit}"></div><div><label class="visually-hidden">Rest in seconds</label><input type="number" min="0" class="form-control form-control-sm rest-input" placeholder="sec"></div><div class="set-actions"><button type="button" class="btn btn-brand btn-sm save-set-btn" aria-label="Save set"><i class="bx bx-check"></i></button><button type="button" class="btn btn-quiet btn-sm remove-set-btn" aria-label="Remove set"><i class="bx bx-trash"></i></button></div>`;
        row.querySelector('.set-number').textContent = row.dataset.setNumber;
        row.querySelector('.reps-input').value = set.reps ?? '';
        row.querySelector('.weight-input').value = set.weight ?? '';
        row.querySelector('.rest-input').value = set.restTime ?? '';
        row.querySelectorAll('input').forEach(input => input.addEventListener('input', () => { row.dataset.dirty = 'true'; }));
        row.querySelector('.save-set-btn').addEventListener('click', async () => {
            try {
                const data = await request('/add_exercise_set', {session_id: session.id, exercise_id: card.dataset.exerciseId, set_number: row.dataset.setNumber, reps: row.querySelector('.reps-input').value, weight: row.querySelector('.weight-input').value, rest_time: row.querySelector('.rest-input').value});
                row.dataset.persisted = 'true'; row.dataset.dirty = 'false'; row.dataset.setId = data.set_id; row.classList.add('set-saved'); showStatus('Set saved.');
            } catch (error) { showStatus(error.message, true); }
        });
        row.querySelector('.remove-set-btn').addEventListener('click', async () => {
            try {
                if (row.dataset.persisted === 'true') await request('/delete_exercise_set', {session_id: session.id, exercise_id: card.dataset.exerciseId, set_number: row.dataset.setNumber});
                row.remove(); renumberSets(card); showStatus('Set removed.');
            } catch (error) { showStatus(error.message, true); }
        });
        return row;
    };
    const persistOrder = () => request('/reorder_session_exercises', {session_id: session.id, exercise_ids: [...exercisesContainer.children].map(card => Number(card.dataset.exerciseId))});
    const createExerciseCard = exercise => {
        const card = document.createElement('article');
        card.className = 'app-card workout-exercise-card'; card.dataset.exerciseId = exercise.id;
        card.innerHTML = `<div class="active-exercise-head">${mediaMarkup(exercise)}<div class="active-exercise-copy"><span class="pill"></span><h2></h2><p></p></div><div class="exercise-order-actions"><button type="button" class="btn btn-quiet btn-sm move-up-btn" aria-label="Move up"><i class="bx bx-up-arrow-alt"></i></button><button type="button" class="btn btn-quiet btn-sm move-down-btn" aria-label="Move down"><i class="bx bx-down-arrow-alt"></i></button><button type="button" class="btn btn-delete btn-sm remove-exercise-btn" aria-label="Remove exercise"><i class="bx bx-trash"></i></button></div></div><div class="set-grid set-grid-head"><span>Set</span><span>Reps</span><span>Weight</span><span>Rest</span><span></span></div><div class="sets-container"></div><button type="button" class="btn btn-quiet btn-sm add-set-btn mt-2"><i class="bx bx-plus"></i>Add set</button>`;
        card.querySelector('.pill').textContent = titleCase(exercise.target || 'Exercise');
        card.querySelector('h2').textContent = exercise.name;
        card.querySelector('.active-exercise-copy p').textContent = titleCase(exercise.equipment || 'No equipment');
        const setsContainer = card.querySelector('.sets-container');
        (exercise.sets || []).forEach(set => setsContainer.appendChild(createSetRow(card, set)));
        card.querySelector('.add-set-btn').addEventListener('click', () => setsContainer.appendChild(createSetRow(card)));
        card.querySelector('.remove-exercise-btn').addEventListener('click', async () => {
            if (!window.confirm(`Remove ${exercise.name} and its logged sets?`)) return;
            try { await request('/remove_session_exercise', {session_id: session.id, exercise_id: exercise.id}); card.remove(); showStatus('Exercise removed.'); } catch (error) { showStatus(error.message, true); }
        });
        card.querySelector('.move-up-btn').addEventListener('click', async () => { if (card.previousElementSibling) { exercisesContainer.insertBefore(card, card.previousElementSibling); try { await persistOrder(); } catch (error) { showStatus(error.message, true); } } });
        card.querySelector('.move-down-btn').addEventListener('click', async () => { if (card.nextElementSibling) { exercisesContainer.insertBefore(card.nextElementSibling, card); try { await persistOrder(); } catch (error) { showStatus(error.message, true); } } });
        return card;
    };
    const renderSession = value => {
        session = value; exercisesContainer.innerHTML = ''; inactivePanel.classList.toggle('d-none', Boolean(session)); activePanel.classList.toggle('d-none', !session);
        if (!session) return;
        nameInput.value = session.name; notesInput.value = session.notes; session.exercises.forEach(exercise => exercisesContainer.appendChild(createExerciseCard(exercise))); startTimer();
    };
    const startWorkout = async routineId => { try { const data = await request('/start_empty_workout', routineId ? {workout_id: routineId} : {}); renderSession(data.session); showStatus(data.created ? 'Workout started.' : 'Your active workout was restored.'); } catch (error) { window.alert(error.message); } };

    const renderSearchResults = (items, append) => {
        if (!append) searchResults.innerHTML = '';
        items.forEach(exercise => {
            const card = document.createElement('article'); card.className = 'exercise-picker-card';
            card.innerHTML = `${mediaMarkup(exercise).replaceAll('active-exercise-media', 'exercise-media')}<div class="exercise-picker-card-body"><h3 class="h6 mb-1"></h3><p class="small text-muted mb-2"></p><button class="btn btn-outline-brand btn-sm w-100" type="button">Add to workout</button></div>`;
            card.querySelector('h3').textContent = exercise.name; card.querySelector('p').textContent = `${titleCase(exercise.target)} · ${titleCase(exercise.equipment)}`;
            card.querySelector('button').addEventListener('click', async () => { try { const data = await request('/add_session_exercise', {session_id: session.id, exercise_id: exercise.id}); exercisesContainer.appendChild(createExerciseCard(data.exercise)); searchModal.hide(); showStatus('Exercise added.'); } catch (error) { showStatus(error.message, true); } });
            searchResults.appendChild(card);
        });
    };
    const loadSearch = async append => {
        loadMore.disabled = true;
        try { const response = await fetch(`${app.dataset.exerciseApi}?${new URLSearchParams({q: searchInput.value.trim(), page: searchPage, per_page: 12})}`); if (!response.ok) throw new Error('Exercises could not be loaded.'); const data = await response.json(); renderSearchResults(data.exercises, append); if (!append && !data.exercises.length) searchResults.innerHTML = '<div class="app-card empty-state"><p class="text-muted mb-0">No matching exercises found.</p></div>'; loadMore.classList.toggle('d-none', searchPage >= data.pages); } catch (error) { if (!append) searchResults.innerHTML = `<div class="alert alert-danger" role="alert">${error.message}</div>`; } finally { loadMore.disabled = false; }
    };

    document.getElementById('custom-workout-btn').addEventListener('click', () => startWorkout());
    document.getElementById('mobile-start-workout').addEventListener('click', () => startWorkout());
    document.querySelectorAll('.start-routine-btn').forEach(button => button.addEventListener('click', () => startWorkout(Number(button.dataset.routineId))));
    document.getElementById('add-exercise-btn').addEventListener('click', () => { searchPage = 1; searchInput.value = ''; loadSearch(false); searchModal.show(); });
    searchInput.addEventListener('input', () => { window.clearTimeout(searchDebounce); searchDebounce = window.setTimeout(() => { searchPage = 1; loadSearch(false); }, 250); });
    loadMore.addEventListener('click', () => { searchPage += 1; loadSearch(true); });
    document.getElementById('save-workout-draft-btn').addEventListener('click', async () => { try { await request('/update_workout_session', {session_id: session.id, name: nameInput.value, notes: notesInput.value}); session.name = nameInput.value.trim(); session.notes = notesInput.value.trim(); showStatus('Workout details saved.'); } catch (error) { showStatus(error.message, true); } });
    document.getElementById('end-workout-btn').addEventListener('click', async () => { if (exercisesContainer.querySelector('.set-row[data-dirty="true"]')) { showStatus('Save or remove every edited set before finishing.', true); return; } try { await request('/end_workout_session', {session_id: session.id, workout_name: nameInput.value, notes: notesInput.value}); window.clearInterval(timerHandle); window.location.href = '/'; } catch (error) { showStatus(error.message, true); } });
    document.getElementById('discard-workout-btn').addEventListener('click', async () => { if (!window.confirm('Discard this workout and every set logged in it?')) return; try { await request('/discard_workout_session', {session_id: session.id}); window.clearInterval(timerHandle); renderSession(null); } catch (error) { showStatus(error.message, true); } });
    renderSession(session);
    const requestedRoutineId = Number(app.dataset.routineId || 0); if (!session && requestedRoutineId) startWorkout(requestedRoutineId);
});
