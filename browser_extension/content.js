// content.js - Injected into all pages to find videos and show the PyDM tooltip

let tooltipDiv = null;
let currentVideo = null;
let tooltipHideTimeout = null;

function initializeTooltip() {
  if (tooltipDiv) return;

  tooltipDiv = document.createElement("div");
  tooltipDiv.className = "pydm-video-tooltip";
  tooltipDiv.innerHTML = `
    <span class="pydm-text-icon">⬇</span>
    <span>Download video</span>
  `;
  tooltipDiv.style.opacity = "0";
  tooltipDiv.style.pointerEvents = "none";
  
  // Hide tooltip when moving mouse out of it
  tooltipDiv.addEventListener("mouseleave", () => {
    scheduleTooltipHide();
  });

  // Keep tooltip visible when hovering it
  tooltipDiv.addEventListener("mouseenter", () => {
    clearTimeout(tooltipHideTimeout);
    tooltipDiv.style.opacity = "1";
    tooltipDiv.style.pointerEvents = "auto";
  });

  // Handle click to download
  tooltipDiv.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!currentVideo) return;
    
    // Send message to background.js
    let videoUrl = currentVideo.src || currentVideo.currentSrc;
    let pageUrl = window.location.href;
    
    // If it's a blob or empty, we must rely on yt-dlp extracting the page URL.
    // Otherwise we can pass the direct MP4 URL if it's a standard video element.
    let isDirectBlob = videoUrl && videoUrl.startsWith('blob:');
    let targetUrl = (videoUrl && !isDirectBlob) ? videoUrl : pageUrl;
    
    // Visually confirm click
    const originalHtml = tooltipDiv.innerHTML;
    tooltipDiv.innerHTML = `<span class="pydm-text-icon">⏳</span><span>Processing...</span>`;
    
    chrome.runtime.sendMessage({
      action: "extract_video",
      url: targetUrl,
      pageUrl: pageUrl,
      title: document.title
    }, (response) => {
      tooltipDiv.innerHTML = `<span class="pydm-text-icon">✅</span><span>Sent to PyDM</span>`;
      setTimeout(() => {
        tooltipDiv.innerHTML = originalHtml;
        hideTooltip();
      }, 2000);
    });
  });

  document.body.appendChild(tooltipDiv);
}

function showTooltip(videoRect) {
  if (!tooltipDiv) initializeTooltip();
  
  clearTimeout(tooltipHideTimeout);
  
  // Position it at the top right of the video
  // Including scroll offset
  const top = window.scrollY + videoRect.top + 8;
  const left = window.scrollX + videoRect.left + videoRect.width - tooltipDiv.offsetWidth - 8;
  
  tooltipDiv.style.top = `${top}px`;
  tooltipDiv.style.left = `${left}px`;
  tooltipDiv.style.opacity = "1";
  tooltipDiv.style.pointerEvents = "auto";
}

function hideTooltip() {
  if (tooltipDiv) {
    tooltipDiv.style.opacity = "0";
    tooltipDiv.style.pointerEvents = "none";
    currentVideo = null;
  }
}

function scheduleTooltipHide() {
  clearTimeout(tooltipHideTimeout);
  tooltipHideTimeout = setTimeout(() => {
    hideTooltip();
  }, 1000); // Wait 1s before hiding allowing mouse to reach the dialog
}

// Track whether PyDM is reachable
let pydmConnected = true;

// Periodically check connection (every 15 seconds)
function checkPydmConnection() {
  try {
    chrome.runtime.sendMessage({ type: "testConnection" }, (response) => {
      pydmConnected = !!(response && response.connected);
    });
  } catch (e) {
    pydmConnected = false;
  }
}
checkPydmConnection();
setInterval(checkPydmConnection, 15000);

// Global mouse tracker to see if we hover a video
document.addEventListener("mousemove", (e) => {
  // Don't show tooltip if PyDM is not running
  if (!pydmConnected) return;

  const element = document.elementFromPoint(e.clientX, e.clientY);

  if (element && element.tagName === "VIDEO") {
    currentVideo = element;
    const rect = element.getBoundingClientRect();

    // Only show if the video is of sensible size (not a tiny tracking pixel)
    if (rect.width > 200 && rect.height > 100) {
      showTooltip(rect);
      return;
    }
  }

  // If we move mouse OUTSIDE tooltip and OUTSIDE video, start hide schedule.
  // Unless we are currently over the tooltip itself
  if (tooltipDiv && !tooltipDiv.contains(e.target)) {
     scheduleTooltipHide();
  }
}, { passive: true });
