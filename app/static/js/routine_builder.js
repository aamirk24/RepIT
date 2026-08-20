document.addEventListener('DOMContentLoaded', () => {
    const builder = document.getElementById('routine-builder');
    if (!builder) return;
    const results = document.getElementById('builder-results');
    const selectedContainer = document.getElementById('selected-exercises');
    const search = document.getElementById('builder-search');
    const loadMore = document.getElementById('load-more-exercises');
    const selected = new Map();
    let page = 1;
    let debounce;
    const titleCase = value => String(value || '').replace(/\b\w/g, letter => letter.toUpperCase());

    const safeMediaUrl = value => {
        if (!value) return '';
        try {
            const url = new URL(value, window.location.origin);
            return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
        } catch { return ''; }
    };

    const mediaMarkup = exercise => {
        const frames = exercise.imageUrls || [];
        if (!frames.length && !exercise.gifUrl) return '<div class="exercise-media"></div>';
        const first = safeMediaUrl(frames[0] || exercise.gifUrl);
        const second = safeMediaUrl(frames[1]);
        if (!first) return '<div class="exercise-media"></div>';
        return `<div class="exercise-media"><img class="exercise-demo-image" src="${first}" data-frame-one="${first}" ${second ? `data-frame-two="${second}"` : ''} data-frame-index="0" alt="" loading="lazy"></div>`;
    };

    const updateSelection = () => {
        selectedContainer.innerHTML = '';
        document.getElementById('selected-count').textContent = selected.size;
        document.getElementById('selected-empty').classList.toggle('d-none', selected.size > 0);
        selected.forEach(exercise => {
            const row = document.createElement('div');
            row.className = 'selected-exercise-row';
            row.innerHTML = `<input type="hidden" name="exercises"><img alt=""><div><strong></strong><small class="d-block text-muted"></small></div><button type="button" class="btn btn-sm btn-quiet" aria-label="Remove exercise"><i class="bx bx-x fs-5"></i></button>`;
            row.querySelector('input').value = Number(exercise.id);
            row.querySelector('img').src = safeMediaUrl((exercise.imageUrls || [exercise.gifUrl || ''])[0]);
            row.querySelector('strong').textContent = exercise.name;
            row.querySelector('small').textContent = `${titleCase(exercise.target)} · ${titleCase(exercise.equipment)}`;
            row.querySelector('button').addEventListener('click', () => { selected.delete(Number(exercise.id)); updateSelection(); renderSelectedStates(); });
            selectedContainer.appendChild(row);
        });
    };

    const renderSelectedStates = () => {
        results.querySelectorAll('[data-exercise-id]').forEach(card => {
            const isSelected = selected.has(Number(card.dataset.exerciseId));
            card.classList.toggle('selected', isSelected);
            const button = card.querySelector('button');
            button.textContent = isSelected ? 'Added' : 'Add exercise';
            button.disabled = isSelected;
        });
    };

    const renderResults = (exercises, append) => {
        if (!append) results.innerHTML = '';
        exercises.forEach(exercise => {
            const card = document.createElement('article');
            card.className = 'exercise-picker-card';
            card.dataset.exerciseId = exercise.id;
            card.innerHTML = `${mediaMarkup(exercise)}<div class="exercise-picker-card-body"><h3 class="h6 mb-1"></h3><p class="small text-muted mb-2"></p><button type="button" class="btn btn-outline-brand btn-sm w-100">Add exercise</button></div>`;
            card.querySelector('h3').textContent = exercise.name;
            card.querySelector('p').textContent = `${titleCase(exercise.target)} · ${titleCase(exercise.equipment)}`;
            card.querySelector('button').addEventListener('click', () => { selected.set(Number(exercise.id), exercise); updateSelection(); renderSelectedStates(); });
            results.appendChild(card);
        });
        renderSelectedStates();
    };

    const load = async append => {
        loadMore.disabled = true;
        const params = new URLSearchParams({q: search.value.trim(), page, per_page: 12});
        try {
            const response = await fetch(`${builder.dataset.exerciseApi}?${params}`);
            if (!response.ok) throw new Error('Exercises could not be loaded.');
            const data = await response.json();
            renderResults(data.exercises, append);
            if (!append && !data.exercises.length) results.innerHTML = '<div class="app-card empty-state"><p class="text-muted mb-0">No matching exercises found.</p></div>';
            document.getElementById('builder-result-count').textContent = `${data.total} exercises`;
            loadMore.classList.toggle('d-none', page >= data.pages);
        } catch (error) {
            if (!append) results.innerHTML = `<div class="alert alert-danger" role="alert">${error.message}</div>`;
        } finally { loadMore.disabled = false; }
    };

    JSON.parse(document.getElementById('selected-exercises-data').textContent).forEach(exercise => selected.set(Number(exercise.id), exercise));
    updateSelection();
    load(false);
    search.addEventListener('input', () => { window.clearTimeout(debounce); debounce = window.setTimeout(() => { page = 1; load(false); }, 250); });
    loadMore.addEventListener('click', () => { page += 1; load(true); });
});
