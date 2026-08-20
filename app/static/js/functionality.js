function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.content : '';
}

function deleteWorkout(workoutId, event) {
    event.stopPropagation();
    fetch('/delete_workout', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify({workoutId})
    }).then(() => { window.location.href = '/'; });
}

function deleteSession(sessionId, event) {
    event.stopPropagation();
    fetch('/delete_session', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify({sessionId})
    }).then(() => { window.location.href = '/'; });
}

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('exerciseSearch');
    if (!searchInput) return;
    const exerciseCards = document.querySelectorAll('.exercise-card');
    const exerciseCount = document.getElementById('exerciseCount');
    const totalExercises = exerciseCards.length;

    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        let visibleCount = 0;
        exerciseCards.forEach(card => {
            const isVisible = !searchTerm || card.dataset.name.includes(searchTerm) || card.dataset.target.includes(searchTerm);
            card.style.display = isVisible ? 'block' : 'none';
            if (isVisible) visibleCount += 1;
        });
        exerciseCount.textContent = `${visibleCount} of ${totalExercises}`;
    });
});
