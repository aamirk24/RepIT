document.addEventListener('DOMContentLoaded', () => {
    const demonstrations = document.querySelectorAll('.exercise-demo-image[data-frame-two]');
    if (!demonstrations.length) {
        return;
    }

    const visibleDemonstrations = new Set();
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                visibleDemonstrations.add(entry.target);
            } else {
                visibleDemonstrations.delete(entry.target);
            }
        });
    });

    demonstrations.forEach((image) => observer.observe(image));

    window.setInterval(() => {
        visibleDemonstrations.forEach((image) => {
            const showSecondFrame = image.dataset.frameIndex === '0';
            image.src = showSecondFrame ? image.dataset.frameTwo : image.dataset.frameOne;
            image.dataset.frameIndex = showSecondFrame ? '1' : '0';
        });
    }, 1200);
});
