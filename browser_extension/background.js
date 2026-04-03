/**
 * PyDM Browser Extension — Background Service Worker
 *
 * Captures browser downloads, cancels them, and forwards the URL
 * to the PyDM application via Native Messaging.
 *
 * Uses onDeterminingFilename to intercept BEFORE the "Save As" dialog.
 */

const NATIVE_HOST_NAME = "com.pydm.native";

// Cooldown: ignore downloads for 3 seconds after extension loads
let startupCooldown = true;
setTimeout(() => { startupCooldown = false; }, 3000);

// Track recently forwarded URLs to avoid duplicates
const recentUrls = new Map();

// Track download IDs that we've decided to intercept
const interceptedIds = new Set();

const DEFAULT_SETTINGS = {
  enabled: true,
  interceptAll: true,
  captureExtensions: [
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
    ".exe", ".msi", ".deb", ".rpm", ".AppImage",
    ".iso", ".img",
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".mp3", ".flac", ".wav", ".aac", ".ogg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".apk",
  ],
  ignorePatterns: [
    "chrome://", "chrome-extension://", "about:", "blob:", "data:",
    "moz-extension://", "edge://", "brave://",
  ],
};

let settings = { ...DEFAULT_SETTINGS };
let nativePort = null;
let pydmRunning = false;

// -------------------------------------------------------------------
// Settings
// -------------------------------------------------------------------

async function loadSettings() {
  try {
    const stored = await chrome.storage.local.get("pydm_settings");
    if (stored.pydm_settings) {
      settings = { ...DEFAULT_SETTINGS, ...stored.pydm_settings };
    }
  } catch (e) {
    console.error("PyDM: Failed to load settings", e);
  }
}

async function saveSettings(newSettings) {
  settings = { ...settings, ...newSettings };
  await chrome.storage.local.set({ pydm_settings: settings });
}

// -------------------------------------------------------------------
// Native Messaging
// -------------------------------------------------------------------

function connectNative() {
  try {
    nativePort = chrome.runtime.connectNative(NATIVE_HOST_NAME);
    nativePort.onMessage.addListener((msg) => {
      console.log("PyDM: Response:", msg);
      pydmRunning = true;
    });
    nativePort.onDisconnect.addListener(() => {
      console.log("PyDM: Disconnected", chrome.runtime.lastError?.message || "");
      nativePort = null;
      pydmRunning = false;
    });
    pydmRunning = true;
    return true;
  } catch (e) {
    console.error("PyDM: Connect failed:", e);
    nativePort = null;
    pydmRunning = false;
    return false;
  }
}

function sendToNative(message) {
  if (!nativePort) {
    if (!connectNative()) {
      pydmRunning = false;
      return false;
    }
  }
  try {
    nativePort.postMessage(message);
    pydmRunning = true;
    return true;
  } catch (e) {
    console.error("PyDM: Send error:", e);
    nativePort = null;
    pydmRunning = false;
    return false;
  }
}

// -------------------------------------------------------------------
// Cookie extraction
// -------------------------------------------------------------------

async function getCookiesForUrl(url) {
  try {
    if (!chrome.cookies) return "";
    const cookies = await chrome.cookies.getAll({ url });
    return cookies.map((c) => `${c.name}=${c.value}`).join("; ");
  } catch (e) {
    return "";
  }
}

// -------------------------------------------------------------------
// Helper: check if URL/filename should be captured
// -------------------------------------------------------------------

function shouldCaptureUrl(url, filename) {
  if (!settings.enabled) return false;
  if (startupCooldown) return false;

  // Skip ignored URL patterns
  if (settings.ignorePatterns.some((p) => url.startsWith(p))) return false;

  // Skip duplicate URLs within 2 seconds
  const now = Date.now();
  if (recentUrls.has(url) && (now - recentUrls.get(url)) < 2000) return false;

  // If interceptAll, capture everything
  if (settings.interceptAll) return true;

  // Check file extension
  if (filename) {
    const lower = filename.toLowerCase();
    return settings.captureExtensions.some((ext) => lower.endsWith(ext));
  }

  return false;
}

// -------------------------------------------------------------------
// Download interception — onDeterminingFilename
// This fires BEFORE the "Save As" dialog, so we can cancel it cleanly.
// -------------------------------------------------------------------

chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
  const url = downloadItem.url || "";
  const filename = downloadItem.filename || "";

  if (!shouldCaptureUrl(url, filename)) {
    // Don't intercept — let browser handle normally
    suggest();
    return;
  }

  console.log(`PyDM: Intercepting — ${filename || url.substring(0, 80)}`);

  // Mark as intercepted so onChanged can handle it
  interceptedIds.add(downloadItem.id);

  // Mark URL as recently processed
  recentUrls.set(url, Date.now());
  if (recentUrls.size > 50) {
    const cutoff = Date.now() - 10000;
    for (const [k, v] of recentUrls) { if (v < cutoff) recentUrls.delete(k); }
  }

  // Cancel the download to prevent the Save dialog
  chrome.downloads.cancel(downloadItem.id, () => {
    chrome.downloads.erase({ id: downloadItem.id });
  });

  // We MUST call suggest() to let Chrome continue its internal state machine, 
  // even though we just cancelled it.
  suggest();

  // Forward to PyDM asynchronously
  (async () => {
    const cookies = await getCookiesForUrl(url);
    const referer = downloadItem.referrer || "";

    const sent = sendToNative({
      action: "download",
      url,
      filename,
      referer,
      cookies,
    });

    if (!sent) {
      console.error("PyDM: Not connected. Is PyDM running?");
      try { await chrome.downloads.download({ url }); } catch {}
    }

    // Close any blank tabs that were spawned for this download
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      for (const tab of tabs) {
        if (tab.url && (
          tab.url === "about:blank" ||
          tab.url === "about:blank#blocked" ||
          tab.url === url
        )) {
          try { await chrome.tabs.remove(tab.id); } catch {}
        }
      }
    } catch (e) {
      console.log("Could not close tab:", e);
    }
  })();

  // Return true because we are not using async suggest in the listener signature,
  // but wait, we already called suggest() synchronously above. So we don't strictly need to return true
  // unless we call suggest() asynchronously. Since suggest() is called synchronously above, returning false/undefined is fine.
  return;
});

// Clean up intercepted IDs when download state changes
chrome.downloads.onChanged.addListener((delta) => {
  if (interceptedIds.has(delta.id)) {
    if (delta.state && (delta.state.current === "interrupted" || delta.state.current === "complete")) {
      interceptedIds.delete(delta.id);
      // Clean up the entry from the download list
      chrome.downloads.erase({ id: delta.id });
    }
  }
});

// -------------------------------------------------------------------
// Message handling from popup
// -------------------------------------------------------------------

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "getSettings") {
    sendResponse({ settings, pydmRunning });
  } else if (msg.type === "updateSettings") {
    saveSettings(msg.settings).then(() => sendResponse({ ok: true }));
    return true;
  } else if (msg.type === "testConnection") {
    const connected = sendToNative({ action: "ping" });
    pydmRunning = connected;
    sendResponse({ connected });
  } else if (msg.action === "extract_video") {
    // Forward the video extraction request to PyDM
    sendToNative({
      action: "extract_video",
      url: msg.url,
      pageUrl: msg.pageUrl,
      title: msg.title
    });
    sendResponse({ ok: true });
    return true;
  }
});

// -------------------------------------------------------------------
// Init
// -------------------------------------------------------------------

loadSettings();
console.log("PyDM: Extension loaded");
