(function () {
  // Configuration
  const scriptTag = document.currentScript;
  const apiKey = scriptTag.getAttribute('data-api-key');
  const hostUrl = scriptTag.getAttribute('data-host') || 'http://localhost:3001';

  if (!apiKey) {
    console.error("AI Widget: Missing data-api-key attribute on script tag.");
    return;
  }

  // Generate or retrieve session ID from localStorage
  const SESSION_KEY = `ai_widget_session_${apiKey}`;
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = Math.random().toString(36).substring(2, 15);
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  // Create toggle button
  const button = document.createElement('button');
  button.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  `;
  button.style.position = 'fixed';
  button.style.bottom = '20px';
  button.style.right = '20px';
  button.style.width = '60px';
  button.style.height = '60px';
  button.style.borderRadius = '30px';
  button.style.backgroundColor = '#4F46E5';
  button.style.color = 'white';
  button.style.border = 'none';
  button.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
  button.style.cursor = 'pointer';
  button.style.zIndex = '999999';
  button.style.display = 'flex';
  button.style.alignItems = 'center';
  button.style.justifyContent = 'center';
  button.style.transition = 'transform 0.2s ease, background-color 0.2s ease';

  button.onmouseover = () => button.style.backgroundColor = '#4338CA';
  button.onmouseout = () => button.style.backgroundColor = '#4F46E5';

  // Create iframe container
  const container = document.createElement('div');
  container.style.position = 'fixed';
  container.style.bottom = '90px';
  container.style.right = '20px';
  container.style.width = '400px';
  container.style.height = '600px';
  container.style.maxWidth = 'calc(100vw - 40px)';
  container.style.maxHeight = 'calc(100vh - 110px)';
  container.style.backgroundColor = 'transparent';
  container.style.borderRadius = '16px';
  container.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.15)';
  container.style.zIndex = '999998';
  container.style.overflow = 'hidden';
  container.style.display = 'none';
  container.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
  container.style.opacity = '0';
  container.style.transform = 'translateY(20px)';

  // Create iframe
  const iframe = document.createElement('iframe');
  iframe.src = `${hostUrl}/embed/chat?api_key=${encodeURIComponent(apiKey)}&session_id=${encodeURIComponent(sessionId)}&origin=${encodeURIComponent(window.location.origin)}`;
  iframe.style.width = '100%';
  iframe.style.height = '100%';
  iframe.style.border = 'none';
  iframe.style.backgroundColor = '#0a0a0a'; // Match dark theme

  container.appendChild(iframe);
  document.body.appendChild(container);
  document.body.appendChild(button);

  // Toggle functionality
  let isOpen = false;
  button.addEventListener('click', () => {
    isOpen = !isOpen;
    if (isOpen) {
      container.style.display = 'block';
      // Small delay to allow display:block to apply before animating opacity
      setTimeout(() => {
        container.style.opacity = '1';
        container.style.transform = 'translateY(0)';
      }, 10);
      button.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      `;
    } else {
      container.style.opacity = '0';
      container.style.transform = 'translateY(20px)';
      setTimeout(() => {
        container.style.display = 'none';
      }, 200);
      button.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      `;
    }
  });
})();
