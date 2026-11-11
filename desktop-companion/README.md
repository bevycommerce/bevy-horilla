# BevyLoop (desktop app)

A small program that sits next to your clock (Windows tray) or at the top of the screen (macOS menu bar). It lets an employee:

- start and end the work day (Sign In / Sign Out) without opening the browser,
- end a break,
- write the Midday note and the End-of-Day note,
- see what is still to do today,
- get a pop-up reminder when something is due (sign in, Midday note, End-of-Day note, sign out).

It talks to the Horilla HR portal (Smart Employee Workspace). It does not keep any work data of its own.

There is no "Take a Break" button on purpose (owner decision).

## IMPORTANT: what has and has not been tested

| Area | Status |
|---|---|
| The program logic (login, token refresh, retries, reminder de-duplication, timer, URL checks) | Automatic tests pass (`npm test`). |
| Window screens, login, sign in/out, notes, logout against a fake local server | Run once on Linux with a virtual screen. Works. |
| Windows installer and zip build | Built on Linux. **Never installed or run on Windows yet.** |
| Windows tray icon, pop-up position, notification buttons, start-at-login | **NOT TESTED on Windows.** |
| Saving the login safely with Windows (DPAPI) | **NOT TESTED on Windows.** |
| macOS | **NOT TESTED. Do not rely on it.** |
| Talking to the real Horilla server | **NOT TESTED** (only a fake server that copies the API shapes). |

Please follow the checklist in "First test on your Windows PC" below before giving this to colleagues.

## How to install (Windows)

1. Get the file `BevyLoop Setup 0.2.0.exe` (made by `npm run build:win`, found in the `dist` folder).
2. Double-click it. Windows may show a blue "Windows protected your PC" box because the program is **not signed**. Click "More info", then "Run anyway". (A paid code-signing certificate removes this warning. We do not have one yet.)
3. Choose the install folder (or keep the default) and finish. The installer makes a **Start Menu shortcut called "BevyLoop"**.
4. Start "BevyLoop" from the Start Menu. A small clock icon appears near the clock (you may need to click the small up-arrow `^` to see it).

**Why the Start Menu shortcut matters:** Windows only shows notification pop-ups with buttons for programs that were installed with a Start Menu shortcut. If you only unzip the zip file and run the exe, notifications may show without buttons or not at all. Clicking the notification still opens the app.

The exe is unsigned. Its icon and name (BevyLoop) are written into the file by `scripts/after-pack.js` (it uses the `resedit` package, no Windows needed).

A zip version is also made (`BevyLoop-0.2.0-win.zip`). Unzip and run `BevyLoop.exe`. Use the installer for real use.

## First run

1. A window opens with "Welcome to BevyLoop".
2. **Server address**:
   - On the same PC that runs the portal: `http://localhost:8000`
   - For colleagues: the portal must be on the internet or company network with **HTTPS**, for example `https://hr.yourcompany.com`. Plain `http://` to anything other than this PC shows a red warning and you must tick a box to continue. Do not do this on a shared network.
3. Type your normal portal **User name** and **Password**, then click **Sign in**.
4. The password is used once to log in and is **never saved**. A "login key" is saved so you do not have to type the password each time. It is encrypted by Windows (DPAPI) or the macOS Keychain.
   - If the computer cannot encrypt it, nothing is saved and the app says you must log in every time you start it.
5. Close the window with "Close" (or click anywhere else). The app keeps running in the tray. To stop it, right-click the tray icon and choose **Quit**.

If the login key stops working (for example, you changed your password in the portal), the app returns to the login screen by itself.

## Daily use

- **Left-click** the tray icon: opens or closes the small window. "Pin" keeps it open.
- **Right-click** the tray icon: menu with status, Sign In / Sign Out (or End Break), Open Workspace, Settings, Quit.
- The big button shows "Start Your Day", "Sign Out", "End Break" or "Sign In Again" depending on your status.
- The notes area follows what the portal says you can send:
  - "Quick Midday note" with **Submit** and **Skip Midday**. After Skip, choose "Write it later" or "Combine with End of Day".
  - "Write your whole day in one note" (when you chose to combine) or "End-of-Day note".
  - "Midday note" if you chose to write it later.
- **Edit and delete:** under "Already sent today", each note has **Edit** and **Delete**.
  - Edit opens the text in a box. **Save** sends the change, **Cancel** closes it.
  - Delete asks "Delete this update? It will be removed completely and cannot be brought back." inside the app window. After you confirm, you can send that kind of note again.
  - Both need the internet. They are never saved for later. Offline you see "You are offline. Please try again when the connection is back."
  - The green message is the server's own answer.
- "Open full editor" opens the detailed page in your browser. Sign in and sign out never need the browser.
- Every button shows **Saving...** and is disabled until the server answers. A green message appears only when the server really said yes. If the server says no, you see its message in red.

## Reminders and notifications

- The app asks the server for status and reminders every 60 seconds, and right when you open the window.
- Each reminder shows one pop-up only (the app remembers this per day, even after a restart).
- Buttons by reminder:
  - Sign in: **Sign In Now**, **Snooze 15 min**
  - Sign out: **Sign Out Now**, **Snooze 15 min**
  - Midday: **Skip Midday (combine)**, **Snooze 15 min**
  - End of day: **Write update**, **Snooze 15 min**
- Clicking the pop-up itself (not a button) opens the window.
- After "Sign In Now" or "Sign Out Now" you get a confirmation pop-up such as "Signed in at 09:02", or the server's error.
- Turn pop-ups off in Settings ("Show desktop notifications").
- Known quirk: if Windows reports a button press for a pop-up the app no longer holds in memory, the app cannot tell which pop-up it was. In that case it only opens the window and never guesses an action.

## Offline behaviour

- Every action gets a unique ID (an "Idempotency-Key") at the moment you click.
- If the computer cannot reach the server, you see **"Not saved yet - no connection. We will retry."** and a yellow bar "1 action waiting to be sent" with a **Retry** button.
- The waiting action is saved in a file, so it survives closing the app. It is retried every 30 seconds, when the network comes back, and when you click Retry. The same ID is used every time, so the server applies it only once, even if an earlier try had secretly worked.
- If the server later answers "no" (for example "You already sent this update"), the action is removed and you see the server's message.
- If you log out, or log in as a different person, waiting actions are discarded so they can never be sent for the wrong person. The app tells you when this happens.
- Time of the action: the server records the time when it receives the request, not the time you clicked. A sign-in saved offline is stamped when it is finally delivered. Use "Fix My Times" in the portal if that matters.

## Settings

- Server address (to change it: log out, then log in again with the new address).
- Show desktop notifications.
- Start BevyLoop when I sign in to my computer (only works in the installed app).
- Log out (tells the server to end the session and deletes the saved login key).
- App version.

## Making the macOS version (NOT TESTED)

- It must be built **on a Mac** (`npm run build:mac`). It cannot be built on Windows or Linux.
- To open without warnings on other Macs, you need an **Apple Developer account** (paid) to sign and notarize the app.
- Notification buttons on macOS need a signed app and the notification style set to "Alerts" in macOS System Settings.
- No macOS icon (`.icns`) is included yet. None of this has been tried. Treat macOS as not supported.

## First test on your Windows PC (checklist)

1. Install with the installer. Does the Start Menu entry "BevyLoop" exist?
2. Start it. Does the clock icon show in the tray? Does left-click open a window near the icon, and does it close when you click elsewhere?
3. Log in with `http://localhost:8000` and a real user. Does your name and "Not Signed In" appear?
4. Click Start Your Day. Check in the portal that the attendance row exists, and that the source says "desktop". Click Sign Out.
5. Write a Midday note and an End-of-Day note. Check they appear in the portal.
6. Wait for a reminder to become due (ask the developer how to make one due sooner for testing). Do you see a pop-up WITH buttons? Do "Sign In Now", "Snooze 15 min", "Skip Midday (combine)" and "Write update" work? Does a plain click open the window?
7. Turn off Wi-Fi, click Start Your Day. Do you see "Not saved yet"? Turn Wi-Fi on. Does it send by itself within about 30 seconds, and only once?
8. Quit and start again. Are you still logged in? Is no reminder shown twice?
9. Settings: tick "Start BevyLoop when I sign in to my computer", restart Windows, check it starts.
10. Log out. Check you are back at the login screen.

Write down anything that does not work exactly as described and tell the developer.

## For developers

Needs Node.js 22 or newer.

```
cd desktop-companion
npm install
npm test            # automatic tests, no Electron needed
npm start           # run the app (unpackaged: notification buttons and start-at-login may not work)
npm run build:win   # Windows installer + zip into dist/
npm run make-icons  # re-draws the icons in assets/
```

Building the Windows installer (`npm test` first, then `npm run build:win`; output in `dist/`, for example `BevyLoop Setup 0.2.0.exe`):
- On Windows it just works.
- On Linux, electron-builder runs `wine` only to make the NSIS uninstaller. Real wine is not needed: put a small stand-in script named `wine` on the PATH (for example `/usr/local/bin/wine`, a Node script, `chmod +x`). It takes the installer path as its first argument and calls `UninstallerReader.exec(installer, uninstaller)` from `app-builder-lib/out/targets/nsis/nsisUtil` (electron-builder's own JavaScript reader), writing `<installer name without exe>__uninstaller.exe` next to it. The zip does not need wine.
- The build uses `signAndEditExecutable: false` (no Windows tools). The `afterPack` hook `scripts/after-pack.js` then writes the icon and version details into `BevyLoop.exe`. The build log shows an "afterPack: icon and version details written" line when it ran.
- A Linux-built installer has **not been run on Windows**. If it misbehaves, build on a Windows PC.

Layout:

- `src/core/` plain logic, tested without Electron: `api.js` (HTTP, token refresh), `token-store.js`, `pending-queue.js`, `shown-store.js`, `settings-store.js`, `workspace.js` (actions and keys), `controller.js` (polling, state), `url.js`, `time.js`, `reminders.js`.
- `src/main/` Electron glue: `main.js`, `tray.js`, `window.js`, `notifications.js`, `ipc.js`.
- `src/preload/preload.js` the only bridge to the window.
- `src/renderer/` the window (HTML, CSS, plain JavaScript).
- `test/` unit tests (`node --test`).

Security design: the window has no Node access (contextIsolation on, nodeIntegration off, sandbox on), a strict Content-Security-Policy, cannot open new windows or navigate away, and never sees tokens. All network calls happen in the main process. Tokens and passwords are never logged.

Server API used (base `/api/workspace/v1/`): `status/`, `sign-in/`, `sign-out/`, `break/end/`, `updates/` (read, send), `updates/<id>/` (PATCH edit, DELETE remove), `updates/midday-skip/`, `reminders/`, `reminders/<id>/snooze/`, `reminders/<id>/ack/`; login through `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/logout/`. Every request sends `X-Workspace-Client: desktop`; changes also send an `Idempotency-Key`.

## Known limitations

- Not tested on Windows or macOS (see the table at the top).
- Notification buttons may not work when run unpackaged (`npm start`) or without the Start Menu shortcut.
- The app uses Electron's older synchronous `safeStorage` calls, which Electron 45 marks as deprecated (they still work). Moving to the async calls is a future task.
- The exe is unsigned, so Windows SmartScreen shows a warning on first run.
- Auto-update is not built in. To update, install the new setup file over the old one.
- Offline actions are stamped by the server at delivery time.
- If the portal is down for a long time, waiting actions keep being retried (every 30 seconds) until the server answers with a clear yes or no.
- Status polling is every 60 seconds, so another device's change can take up to a minute to show.
- Only one account per computer user.
