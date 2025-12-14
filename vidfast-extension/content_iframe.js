console.log("Iframe Worker Active");

// 1. Force the 'WebDriver' flag to false (Pass Robot Check)
const script = document.createElement('script');
script.textContent = `
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
`;
(document.head || document.documentElement).appendChild(script);
script.remove();

// 2. The "Wiggler" - Simulates human activity every 500ms
setInterval(() => {
    // Random mouse movement
    const moveEvent = new MouseEvent('mousemove', {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: Math.random() * 500,
        clientY: Math.random() * 500
    });
    document.body.dispatchEvent(moveEvent);

    // Random scroll
    window.scrollBy(0, 1);
}, 500);