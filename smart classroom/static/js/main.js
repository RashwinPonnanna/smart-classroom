/**
 * Smart Classroom Timetable Scheduler - Frontend Logic
 */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
});

/**
 * Show a loading spinner overlay while generating timetable.
 */
function showLoading(message) {
    var overlay = document.createElement('div');
    overlay.className = 'spinner-overlay';
    overlay.id = 'loadingOverlay';
    overlay.innerHTML =
        '<div class="text-center">' +
        '<div class="spinner-border text-primary" style="width:3rem;height:3rem;" role="status"></div>' +
        '<p class="mt-3 text-muted">' + (message || 'Processing...') + '</p>' +
        '</div>';
    document.body.appendChild(overlay);
}

/**
 * Hide the loading spinner.
 */
function hideLoading() {
    var overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.remove();
}

/**
 * Fetch timetable data via API and render as JSON (for debugging).
 */
function fetchTimetableAPI(courseId, semester) {
    var url = '/api/timetable?semester=' + (semester || 5);
    if (courseId) url += '&course_id=' + courseId;

    return fetch(url)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            console.log('Timetable data:', data);
            return data;
        });
}

/**
 * Trigger timetable generation via API.
 */
function generateTimetableAPI(courseId, semester) {
    showLoading('Generating timetable using ML optimization...');

    return fetch('/api/timetable/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            course_id: courseId || null,
            semester: semester || 5,
        }),
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            hideLoading();
            console.log('Generation result:', data);
            return data;
        })
        .catch(function (err) {
            hideLoading();
            console.error('Generation error:', err);
            throw err;
        });
}

/**
 * Add loading state to generate buttons.
 */
document.querySelectorAll('form[action*="generate"]').forEach(function (form) {
    form.addEventListener('submit', function () {
        showLoading('Running ML optimization... This may take a moment.');
    });
});
