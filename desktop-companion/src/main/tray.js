'use strict';

const { Tray, Menu, nativeImage } = require('electron');

/**
 * Tray icon (Windows) / menu bar icon (macOS).
 * handlers: { toggle(), showView(view), act(name), quit() }
 */
function createTray({ iconPath, handlers }) {
  const image = nativeImage.createFromPath(iconPath);
  const tray = new Tray(image);
  tray.setToolTip('BevyLoop');

  let menu = null;
  // No setContextMenu(): on macOS that would make a left click open the menu.
  // We open the menu ourselves on right click so both systems behave the same.
  tray.on('click', () => handlers.toggle());
  tray.on('right-click', () => {
    if (menu) tray.popUpContextMenu(menu);
  });

  function statusLine(snap) {
    if (!snap.loggedIn) return 'Not logged in to the portal';
    let line = `Status: ${snap.statusLabel}`;
    if (snap.offline) line += ' (no connection)';
    return line;
  }

  function update(snap) {
    const tip = ['BevyLoop', statusLine(snap)];
    if (snap.pendingCount) tip.push(`${snap.pendingCount} waiting to be sent`);
    tray.setToolTip(tip.join('\n'));

    const items = [{ label: statusLine(snap), enabled: false }, { type: 'separator' }];
    if (!snap.loggedIn) {
      items.push({ label: 'Log in to BevyLoop', click: () => handlers.showView('settings') });
    } else {
      const st = snap.status ? snap.status.status : null;
      if (st === 'on_break') items.push({ label: 'End Break', click: () => handlers.act('end_break') });
      else if (st === 'working' || st === 'away') items.push({ label: 'Sign Out', click: () => handlers.act('sign_out') });
      else if (st) items.push({ label: 'Sign In (start my day)', click: () => handlers.act('sign_in') });
    }
    items.push(
      { label: 'Open BevyLoop', click: () => handlers.showView('main') },
      { label: 'Settings', click: () => handlers.showView('settings') },
      { type: 'separator' },
      { label: 'Quit', click: () => handlers.quit() },
    );
    menu = Menu.buildFromTemplate(items);
  }

  return { tray, update, getBounds: () => tray.getBounds(), destroy: () => tray.destroy() };
}

module.exports = { createTray };
