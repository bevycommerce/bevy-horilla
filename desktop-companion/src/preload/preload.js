'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// The smallest possible door to the main process. No tokens ever pass through here.
contextBridge.exposeInMainWorld('bevy', {
  getSnapshot: () => ipcRenderer.invoke('app:get-snapshot'),
  refresh: () => ipcRenderer.invoke('app:refresh'),
  networkOnline: () => ipcRenderer.invoke('app:network-online'),
  login: (input) =>
    ipcRenderer.invoke('auth:login', {
      serverUrl: input && input.serverUrl,
      username: input && input.username,
      password: input && input.password,
      confirmInsecure: !!(input && input.confirmInsecure),
    }),
  checkUrl: (value) => ipcRenderer.invoke('url:check', String(value == null ? '' : value)),
  logout: () => ipcRenderer.invoke('auth:logout'),
  act: (name, payload) => ipcRenderer.invoke('action:run', name, payload),
  retryPending: () => ipcRenderer.invoke('pending:retry'),
  saveSettings: (patch) => ipcRenderer.invoke('settings:save', patch),
  openFullEditor: () => ipcRenderer.invoke('shell:open-editor'),
  setPinned: (value) => ipcRenderer.invoke('window:set-pinned', !!value),
  hideWindow: () => ipcRenderer.invoke('window:hide'),
  onSnapshot: (callback) => {
    const listener = (_event, snap) => callback(snap);
    ipcRenderer.on('snapshot', listener);
    return () => ipcRenderer.removeListener('snapshot', listener);
  },
  onNavigate: (callback) => {
    const listener = (_event, view) => callback(view);
    ipcRenderer.on('navigate', listener);
    return () => ipcRenderer.removeListener('navigate', listener);
  },
});
