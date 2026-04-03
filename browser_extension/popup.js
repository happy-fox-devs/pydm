/**
 * PyDM Extension Popup Script
 */

const enableToggle = document.getElementById("enableToggle");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const testBtn = document.getElementById("testBtn");
const offlineBanner = document.getElementById("offlineBanner");

function updateOfflineUI(connected) {
  if (connected) {
    offlineBanner.classList.remove("visible");
    enableToggle.disabled = false;
  } else {
    offlineBanner.classList.add("visible");
  }
}

// Load current settings
chrome.runtime.sendMessage({ type: "getSettings" }, (response) => {
  if (response && response.settings) {
    enableToggle.checked = response.settings.enabled;
  }
  // Update offline state from background's tracked state
  if (response && typeof response.pydmRunning !== "undefined") {
    updateOfflineUI(response.pydmRunning);
  }
});

// Toggle capture on/off
enableToggle.addEventListener("change", () => {
  chrome.runtime.sendMessage({
    type: "updateSettings",
    settings: { enabled: enableToggle.checked },
  });
});

// Test connection
function testConnection() {
  statusDot.className = "status-dot";
  statusText.textContent = "Checking...";

  chrome.runtime.sendMessage({ type: "testConnection" }, (response) => {
    if (response && response.connected) {
      statusDot.className = "status-dot connected";
      statusText.textContent = "Connected to PyDM ✓";
      updateOfflineUI(true);
    } else {
      statusDot.className = "status-dot disconnected";
      statusText.textContent = "Could not connect";
      updateOfflineUI(false);
    }
  });
}

testBtn.addEventListener("click", testConnection);

// Auto-test on popup open
setTimeout(testConnection, 300);
