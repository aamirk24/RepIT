document.addEventListener('DOMContentLoaded', () => {
    const visible = new Set();
    const observed = new WeakSet();
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => entry.isIntersecting ? visible.add(entry.target) : visible.delete(entry.target));
    }, {rootMargin: '120px'});

    const register = root => {
        const images = root.matches?.('.exercise-demo-image[data-frame-two]')
            ? [root]
            : root.querySelectorAll?.('.exercise-demo-image[data-frame-two]') || [];
        images.forEach(image => {
            if (!observed.has(image)) {
                observed.add(image);
                observer.observe(image);
            }
        });
    };

    register(document);
    new MutationObserver(mutations => mutations.forEach(mutation => mutation.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) register(node);
    }))).observe(document.body, {childList: true, subtree: true});

    window.setInterval(() => {
        visible.forEach(image => {
            const second = image.dataset.frameIndex === '0';
            image.src = second ? image.dataset.frameTwo : image.dataset.frameOne;
            image.dataset.frameIndex = second ? '1' : '0';
        });
    }, 1200);
});
