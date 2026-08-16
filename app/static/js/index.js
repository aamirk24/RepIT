document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('section:not(.hero-section)');

    // Create an Intersection Observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            // Check if the section is intersecting
            if (entry.isIntersecting) {
                const contentElements  = entry.target.querySelectorAll(
                    'h2, h3, p, img, .btn, .row > div'
                );

                // Add fade-in-float class to each content element
                contentElements.forEach((el, index) => {
                    el.style.animationDelay = `${index * 0.1}s`;
                    el.classList.add('fade-in-float');
                });

                // Unobserve the section
                observer.unobserve(entry.target);
            }
        });
    }, {
        // Trigger when at least 10% of the section is visible
        threshold: 0.1
    });

    // Start observing each section
    sections.forEach(section => {
        observer.observe(section);
    });
});