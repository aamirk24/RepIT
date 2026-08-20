function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.content : '';
}

async function deleteRecord(url, body, redirectUrl = '') {
    const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
        body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error('The item could not be deleted.');
    if (redirectUrl) window.location.assign(redirectUrl);
    else window.location.reload();
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-delete-workout-id]').forEach(button => {
        button.addEventListener('click', async event => {
            event.stopPropagation();
            if (!window.confirm('Delete this routine? Completed workout history will be retained.')) return;
            try {
                await deleteRecord('/delete_workout', {workoutId: button.dataset.deleteWorkoutId}, button.dataset.deleteRedirect);
            } catch (error) { window.alert(error.message); }
        });
    });
    document.querySelectorAll('[data-delete-session-id]').forEach(button => {
        button.addEventListener('click', async event => {
            event.stopPropagation();
            if (!window.confirm('Permanently delete this workout from your history?')) return;
            try {
                await deleteRecord('/delete_session', {sessionId: button.dataset.deleteSessionId});
            } catch (error) { window.alert(error.message); }
        });
    });

});
