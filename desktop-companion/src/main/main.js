'use strict';

const path = require('node:path');
const { app, net, safeStorage, powerMonitor } = require('electron');

const APP_ID = 'com.bevycommerce.workspace';
const POLL_MS = 60 * 1000;
const RETRY_MS = 30 * 1000;

// Windows needs this before any notification so toasts belong to the Start Menu shortcut.
if (process.platform === 'win32') app.setAppUserModelId(APP_ID);

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  start();
}

function start() {
  const { createApiClient } = require('../core/api');
  const { createTokenStore } = require('../core/token-store');
  const { createPendingQueue } = require('../core/pending-queue');
  const { createShownStore } = require('../core/shown-store');
  const { createSettingsStore, NO_POSITION } = require('../core/settings-store');
  const { createWorkspace } = require('../core/workspace');
  const { createController } = require('../core/controller');
  const { createPopup } = require('./window');
  const { createTray } = require('./tray');
  const { createNotifier } = require('./notifications');
  const { registerIpc } = require('./ipc');

  let popup = null;
  let trayHandle = null;

  app.on('second-instance', () => {
    if (popup) popup.show();
  });

  // Keep running in the tray when the window is closed.
  app.on('window-all-closed', () => {});

  const AUTOSTART_ARG = '--autostart';
  const startedAtLogin =
    process.argv.includes(AUTOSTART_ARG) ||
    (process.platform === 'darwin' && (() => { try { return app.getLoginItemSettings().wasOpenedAtLogin; } catch (e) { return false; } })());

  app.whenReady().then(() => {
    if (process.platform === 'darwin' && app.dock) app.dock.hide();

    const dataDir = app.getPath('userData');
    const assets = path.join(__dirname, '..', '..', 'assets');
    const settings = createSettingsStore({ filePath: path.join(dataDir, 'settings.json') });
    const tokenStore = createTokenStore({ filePath: path.join(dataDir, 'session.bin.json'), safeStorage });
    const shown = createShownStore({ filePath: path.join(dataDir, 'shown-reminders.json') });

    let controller = null;
    const api = createApiClient({
      fetchImpl: (url, init) => net.fetch(url, init),
      getServerUrl: () => (controller ? controller.getServerUrl() : settings.get().serverUrl),
      tokenStore,
    });
    const workspace = createWorkspace({ api });
    const queue = createPendingQueue({
      filePath: path.join(dataDir, 'pending.json'),
      send: (item) => api.request(item.method, item.path, { body: item.body, key: item.key }),
    });
    workspace.attachQueue(queue);

    let notifier = null;
    controller = createController({
      api,
      workspace,
      queue,
      shown,
      settings,
      tokenStore,
      extras: () => ({
        appVersion: app.getVersion(),
        openAtLogin: safeLoginState(),
        canAutoStart: app.isPackaged && (process.platform === 'win32' || process.platform === 'darwin'),
      }),
      onChange: (snap) => {
        if (trayHandle) trayHandle.update(snap);
        if (popup && !popup.win.isDestroyed()) popup.win.webContents.send('snapshot', snap);
        if (notifier && snap && snap.loggedIn && Array.isArray(snap.reminders)) notifier.sync(snap.reminders);
      },
      onNewReminders: (list) => {
        if (notifier) list.forEach((r) => notifier.showReminder(r));
      },
    });

    popup = createPopup({
      iconPath: path.join(assets, 'icon.png'),
      getTrayBounds: () => (trayHandle ? trayHandle.getBounds() : null),
      getSavedPosition: () => {
        const { windowX, windowY } = settings.get();
        return windowX === NO_POSITION || windowY === NO_POSITION ? null : { x: windowX, y: windowY };
      },
      savePosition: ({ x, y }) => settings.set({ windowX: x, windowY: y }),
      isDev: !app.isPackaged,
    });

    notifier = createNotifier({
      controller,
      showPopup: (view) => popup.show(view),
      iconPath: path.join(assets, 'icon.png'),
    });
    notifier.init();

    const refreshAndFlush = async () => {
      await controller.flushQueue();
      await controller.poll();
    };

    trayHandle = createTray({
      iconPath: path.join(assets, 'tray.png'),
      handlers: {
        toggle: () => {
          popup.toggle();
        },
        showView: (view) => popup.show(view),
        act: async (name) => {
          const result = await controller.perform(name);
          notifier.info(result.message);
        },
        quit: () => {
          popup.markQuitting();
          app.quit();
        },
      },
    });

    registerIpc({
      controller,
      popup,
      refreshAndFlush,
      setLoginItem: (enabled) => {
        if (!app.isPackaged) {
          return { ok: false, message: 'This only works in the installed app, not in a test run.' };
        }
        if (process.platform !== 'win32' && process.platform !== 'darwin') {
          return { ok: false, message: 'This is only available on Windows and macOS.' };
        }
        app.setLoginItemSettings({ openAtLogin: enabled, args: enabled ? [AUTOSTART_ARG] : [] });
        return { ok: true, message: '' };
      },
    });

    popup.win.on('show', () => {
      controller.poll();
    });

    trayHandle.update(controller.snapshot());

    setInterval(() => controller.poll(), POLL_MS);
    setInterval(() => controller.flushQueue(), RETRY_MS);
    powerMonitor.on('resume', () => refreshAndFlush());

    if (controller.snapshot().loggedIn) {
      refreshAndFlush();
      // Opened by the person (Start menu, desktop icon, "Run BevyLoop" after install): show the window.
      // Started by Windows at sign-in: stay quietly in the tray.
      if (!startedAtLogin) popup.show('main');
    } else {
      popup.show('settings'); // first run: show the login screen
    }
  });

  function safeLoginState() {
    try {
      // Windows matches the saved entry including its arguments
      return app.getLoginItemSettings({ args: [AUTOSTART_ARG] }).openAtLogin;
    } catch (e) {
      return false;
    }
  }

  app.on('before-quit', () => {
    if (popup) popup.markQuitting();
  });
}
