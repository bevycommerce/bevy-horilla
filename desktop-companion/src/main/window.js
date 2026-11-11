'use strict';

const path = require('node:path');
const { BrowserWindow, screen, session } = require('electron');

const WIDTH = 380;
const HEIGHT = 560;

/** The small popup near the tray icon. */
/**
 * Owner rule (2026-11-11): the window can be dragged anywhere by its top bar and
 * stays open until Close (or a tray click). It remembers where it was put.
 * getSavedPosition() -> {x, y} | null, savePosition({x, y}).
 */
function createPopup({ iconPath, getTrayBounds, isDev, getSavedPosition = () => null, savePosition = () => {} }) {
  let pinned = false;

  const win = new BrowserWindow({
    width: WIDTH,
    height: HEIGHT,
    show: false,
    frame: false,
    resizable: false,
    maximizable: false,
    minimizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    title: 'BevyLoop',
    icon: iconPath,
    backgroundColor: '#ffffff',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      devTools: !!isDev,
    },
  });

  // The window never opens other windows or leaves our own page.
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event) => event.preventDefault());
  win.webContents.on('will-redirect', (event) => event.preventDefault());
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, callback) => callback(false));

  win.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  let saveTimer = null;
  win.on('moved', () => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      const [x, y] = win.getPosition();
      savePosition({ x, y });
    }, 300);
  });

  // Closing the window only hides it. Quit is in the tray menu.
  let quitting = false;
  win.on('close', (event) => {
    if (!quitting) {
      event.preventDefault();
      win.hide();
    }
  });

  function savedPositionStillOnScreen() {
    const saved = getSavedPosition();
    if (!saved) return null;
    const area = screen.getDisplayMatching({ x: saved.x, y: saved.y, width: WIDTH, height: HEIGHT }).workArea;
    const visibleX = Math.min(saved.x + WIDTH, area.x + area.width) - Math.max(saved.x, area.x);
    const visibleY = Math.min(saved.y + HEIGHT, area.y + area.height) - Math.max(saved.y, area.y);
    // at least the top bar must be reachable, otherwise fall back to the tray position
    return visibleX >= 120 && visibleY >= 60 && saved.y >= area.y ? saved : null;
  }

  function position() {
    const saved = savedPositionStillOnScreen();
    if (saved) {
      win.setPosition(saved.x, saved.y, false);
      return;
    }
    const bounds = getTrayBounds ? getTrayBounds() : null;
    const point = bounds && (bounds.width || bounds.height)
      ? { x: bounds.x + bounds.width / 2, y: bounds.y + bounds.height / 2 }
      : screen.getCursorScreenPoint();
    const display = screen.getDisplayNearestPoint(point);
    const area = display.workArea;
    let x = Math.round(point.x - WIDTH / 2);
    let y = point.y > area.y + area.height / 2 ? Math.round(point.y - HEIGHT - 12) : Math.round(point.y + 12);
    if (!bounds || !(bounds.width || bounds.height)) {
      x = area.x + area.width - WIDTH - 12;
      y = area.y + area.height - HEIGHT - 12;
    }
    x = Math.max(area.x + 8, Math.min(x, area.x + area.width - WIDTH - 8));
    y = Math.max(area.y + 8, Math.min(y, area.y + area.height - HEIGHT - 8));
    win.setPosition(x, y, false);
  }

  function show(view) {
    position();
    win.show();
    win.focus();
    if (view) {
      if (win.webContents.isLoading()) win.webContents.once('did-finish-load', () => win.webContents.send('navigate', view));
      else win.webContents.send('navigate', view);
    }
  }

  function toggle() {
    if (win.isVisible()) win.hide();
    else show();
  }

  return {
    win,
    show,
    toggle,
    hide: () => win.hide(),
    setPinned(value) {
      pinned = !!value;
      win.setAlwaysOnTop(pinned);
    },
    isPinned: () => pinned,
    markQuitting() {
      quitting = true;
    },
  };
}

module.exports = { createPopup };
