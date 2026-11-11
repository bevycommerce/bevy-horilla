'use strict';
/* Window code. It never sees tokens: everything goes through window.bevy (see preload.js). */
(function () {
  const api = window.bevy;
  const $ = (id) => document.getElementById(id);

  let snap = null;
  let view = 'main'; // 'main' | 'settings' (login screen shows automatically when logged out)
  let pinned = false;
  let dismissedNoticeAt = 0;
  let renderedUpdatesKey = '';
  let focusUpdateBox = false;
  const busy = new Set();
  const drafts = { midday: '', eod: '', combined: '' };
  const boxMsg = {}; // per box { kind, text }
  let primaryMsg = null;
  let skipChoiceOpen = false;
  let insecureNeedsTick = false;

  function pad(n) { return String(n).padStart(2, '0'); }
  function formatHMS(total) {
    let s = Math.floor(Number(total));
    if (!Number.isFinite(s) || s < 0) s = 0;
    return pad(Math.floor(s / 3600)) + ':' + pad(Math.floor((s % 3600) / 60)) + ':' + pad(s % 60);
  }
  function clock(iso) {
    const m = /T(\d{2}):(\d{2})/.exec(iso || '');
    return m ? m[1] + ':' + m[2] : '';
  }
  function el(tag, props, children) {
    const node = document.createElement(tag);
    if (props) {
      for (const [k, v] of Object.entries(props)) {
        if (k === 'class') node.className = v;
        else if (k === 'text') node.textContent = v;
        else if (k === 'onclick') node.addEventListener('click', v);
        else if (k === 'oninput') node.addEventListener('input', v);
        else if (v === true) node.setAttribute(k, '');
        else if (v !== false && v != null) node.setAttribute(k, v);
      }
    }
    (children || []).forEach((c) => c && node.appendChild(c));
    return node;
  }
  function setMsg(node, msg) {
    node.className = 'msg' + (msg ? ' ' + msg.kind : '');
    node.textContent = msg ? msg.text : '';
  }
  function resultMsg(result) {
    if (result.ok) return { kind: 'ok', text: result.message || 'Done.' };
    if (result.queued) return { kind: 'error', text: result.message };
    return { kind: 'error', text: result.message || 'Something went wrong.' };
  }

  // ------------------------------------------------------------ actions
  async function run(busyKey, name, payload, setMessage, afterOk) {
    if (busy.has(busyKey)) return;
    busy.add(busyKey);
    setMessage({ kind: 'wait', text: 'Saving...' });
    renderAll();
    let result;
    try {
      result = await api.act(name, payload);
    } catch (e) {
      result = { ok: false, message: 'Something went wrong. Please try again.' };
    }
    busy.delete(busyKey);
    setMessage(resultMsg(result));
    if (result.ok && afterOk) afterOk(result);
    renderAll();
  }

  function primaryAction() {
    const st = snap.status && snap.status.status;
    const name = st === 'on_break' ? 'end_break' : st === 'working' || st === 'away' ? 'sign_out' : 'sign_in';
    run('primary', name, {}, (m) => { primaryMsg = m; });
  }

  // ------------------------------------------------------------ rendering
  function renderBanners() {
    const area = $('banner-area');
    area.textContent = '';
    if (!snap || !snap.loggedIn) {
      if (snap && snap.notice && snap.notice.at !== dismissedNoticeAt) {
        area.appendChild(el('div', { class: 'banner ' + (snap.notice.kind === 'ok' ? 'ok' : 'error') }, [el('span', { text: snap.notice.text })]));
      }
      return;
    }
    if (snap.insecure) {
      area.appendChild(el('div', { class: 'banner warn' }, [el('span', { text: 'This connection is not secure. Do not use a shared network.' })]));
    }
    if (!snap.secureStorage) {
      area.appendChild(el('div', { class: 'banner info' }, [el('span', { text: 'Your login cannot be saved safely on this computer. You will need to log in each time you start the app.' })]));
    }
    if (snap.offline) {
      area.appendChild(el('div', { class: 'banner warn' }, [el('span', { text: 'No connection to the server. Showing the last information we have.' })]));
    } else if (snap.problem) {
      area.appendChild(el('div', { class: 'banner error' }, [el('span', { text: snap.problem })]));
    }
    if (snap.pendingCount > 0) {
      const n = snap.pendingCount;
      area.appendChild(el('div', { class: 'banner warn' }, [
        el('span', { text: n + (n === 1 ? ' action' : ' actions') + ' waiting to be sent' }),
        el('button', { class: 'icon-btn', type: 'button', text: busy.has('retry') ? 'Retrying...' : 'Retry', disabled: busy.has('retry'), onclick: retryPending }),
      ]));
    }
    if (snap.notice && snap.notice.at !== dismissedNoticeAt) {
      area.appendChild(el('div', { class: 'banner ' + (snap.notice.kind === 'ok' ? 'ok' : 'error') }, [
        el('span', { text: snap.notice.text }),
        el('button', { class: 'icon-btn', type: 'button', text: 'OK', onclick: () => { dismissedNoticeAt = snap.notice.at; renderBanners(); } }),
      ]));
    }
  }

  async function retryPending() {
    busy.add('retry');
    renderBanners();
    try { snap = await api.retryPending(); } catch (e) { /* the banner stays */ }
    busy.delete('retry');
    renderAll();
  }

  function renderHeader() {
    const logged = snap && snap.loggedIn;
    $('who-name').textContent = logged ? snap.employeeName || 'BevyLoop' : 'BevyLoop';
    const badge = $('status-badge');
    const st = logged && snap.status ? snap.status.status : 'off';
    badge.className = 'badge badge-' + st;
    badge.textContent = logged ? snap.statusLabel : 'Not Signed In';
    $('btn-pin').className = 'icon-btn' + (pinned ? ' on' : '');
    $('btn-pin').textContent = pinned ? 'Pinned' : 'Pin';
    $('btn-settings').hidden = !logged;
  }

  function renderTimer() {
    if (!snap || !snap.status) { $('timer').textContent = '00:00:00'; return; }
    const s = snap.status;
    let total = Number(s.worked_seconds) || 0;
    if (s.timer_running) total += Math.max(0, Math.floor((Date.now() - snap.receivedAt) / 1000));
    $('timer').textContent = formatHMS(total);
  }

  function renderMain() {
    renderTimer();
    const s = snap.status;
    let line = '';
    if (s && (s.session_started_at || s.signed_in_at)) line = 'Signed in at ' + clock(s.session_started_at || s.signed_in_at);
    if (s && s.status === 'signed_out' && s.signed_out_at) line += (line ? '  |  ' : '') + 'Signed out at ' + clock(s.signed_out_at);
    if (s && s.status === 'on_break') line += (line ? '  |  ' : '') + 'Timer is paused during your break';
    $('signed-line').textContent = line || (s ? 'You have not signed in yet today.' : 'Loading...');

    const btn = $('btn-primary');
    const st = s && s.status;
    btn.className = 'big-btn' + (st === 'working' || st === 'away' ? ' danger' : '');
    if (busy.has('primary')) { btn.textContent = 'Saving...'; btn.disabled = true; }
    else {
      btn.disabled = !s;
      btn.textContent = !s ? 'Loading...' : st === 'on_break' ? 'End Break' : st === 'working' || st === 'away' ? 'Sign Out' : st === 'signed_out' ? 'Sign In Again' : 'Start Your Day';
    }
    setMsg($('primary-msg'), primaryMsg);

    renderUpdates();
    renderSent();
    renderPendingActions();
  }

  function noteBox(type, title, placeholder, extraButtons) {
    const key = 'submit:' + type;
    const area = el('textarea', { placeholder: placeholder || '', 'data-box': type, oninput: (e) => { drafts[type] = e.target.value; } });
    area.value = drafts[type];
    const msgNode = el('div', { class: 'msg' });
    setMsg(msgNode, boxMsg[type]);
    const isBusy = busy.has(key);
    const submit = el('button', {
      class: 'mid-btn', type: 'button', text: isBusy ? 'Saving...' : 'Submit', disabled: isBusy,
      onclick: () => run(key, 'submit_update', { type, summary: drafts[type] }, (m) => { boxMsg[type] = m; }, () => { drafts[type] = ''; }),
    });
    const row = el('div', { class: 'btn-row' }, [submit].concat(extraButtons || []));
    return el('div', { class: 'card' }, [el('div', { class: 'section-title', text: title }), area, row, msgNode]);
  }

  function renderUpdates() {
    const area = $('updates-area');
    const day = snap.day;
    // Only rebuild when something that changes the boxes changed, so typing is never interrupted.
    const key = JSON.stringify([day && [day.can_submit_midday, day.can_skip_midday, day.can_submit_eod, day.recommend_combined, day.midday_pending_later, day.skip], [...busy].sort(), skipChoiceOpen, boxMsg, !!day]);
    if (key === renderedUpdatesKey && !focusUpdateBox) return;
    renderedUpdatesKey = key;
    area.textContent = '';
    if (!day) { area.appendChild(el('div', { class: 'muted small', text: snap.offline ? 'Updates are not available without a connection.' : 'Loading updates...' })); return; }

    if (day.can_submit_midday && !day.recommend_combined) {
      const late = day.midday_pending_later;
      const extra = [];
      if (day.can_skip_midday && !day.skip) {
        extra.push(el('button', { class: 'mid-btn secondary', type: 'button', text: 'Skip Midday', onclick: () => { skipChoiceOpen = true; renderedUpdatesKey = ''; renderUpdates(); } }));
      }
      const box = noteBox('midday', late ? 'Late Midday note' : 'Quick Midday note', 'What are you working on?', extra);
      area.appendChild(box);
      if (skipChoiceOpen && day.can_skip_midday && !day.skip) {
        const msgNode = el('div', { class: 'msg' });
        setMsg(msgNode, boxMsg.skip);
        area.appendChild(el('div', { class: 'card' }, [
          el('div', { class: 'section-title', text: 'Skip Midday' }),
          el('div', { class: 'btn-row' }, [
            el('button', { class: 'mid-btn', type: 'button', text: busy.has('skip') ? 'Saving...' : 'Write it later', disabled: busy.has('skip'), onclick: () => run('skip', 'skip_midday', { choice: 'later' }, (m) => { boxMsg.skip = m; }, () => { skipChoiceOpen = false; }) }),
            el('button', { class: 'mid-btn', type: 'button', text: busy.has('skip') ? 'Saving...' : 'Combine with End of Day', disabled: busy.has('skip'), onclick: () => run('skip', 'skip_midday', { choice: 'combine' }, (m) => { boxMsg.skip = m; }, () => { skipChoiceOpen = false; }) }),
          ]),
          msgNode,
        ]));
      }
    }
    if (day.recommend_combined) {
      area.appendChild(noteBox('combined', 'Write your whole day in one note', 'What did you do today?'));
    } else if (day.can_submit_eod) {
      area.appendChild(noteBox('eod', 'End-of-Day note', 'What did you finish today?'));
    }
    if (focusUpdateBox) {
      focusUpdateBox = false;
      const first = area.querySelector('textarea[data-box="eod"], textarea[data-box="combined"]') || area.querySelector('textarea');
      if (first) first.focus();
    }
  }

  function renderSent() {
    const area = $('sent-area');
    area.textContent = '';
    const day = snap.day;
    if (!day) return;
    const items = [['midday', 'Midday note'], ['eod', 'End-of-Day note'], ['combined', 'Whole-day note']]
      .map(([k, label]) => [day[k], label]).filter(([u]) => u);
    if (!items.length) return;
    area.appendChild(el('div', { class: 'section-title', text: 'Already sent today' }));
    for (const [u, label] of items) {
      const text = u.summary.length > 160 ? u.summary.slice(0, 160) + '...' : u.summary;
      area.appendChild(el('div', { class: 'sent-item' }, [
        el('div', { text: text || '(no text)' }),
        el('div', { class: 'meta', text: label + ' sent at ' + clock(u.submitted_at) + (u.is_late ? ' (late)' : '') }),
      ]));
    }
  }

  function renderPendingActions() {
    const area = $('pending-area');
    area.textContent = '';
    const list = snap.pendingActions || [];
    area.appendChild(el('div', { class: 'section-title', text: 'Still to do' }));
    if (!list.length) { area.appendChild(el('div', { class: 'muted small', text: 'Nothing waiting for you right now.' })); return; }
    area.appendChild(el('ul', { class: 'plain' }, list.map((a) => el('li', { text: a.label }))));
  }

  function renderSettings() {
    $('set-server').textContent = snap.serverUrl || '(not set)';
    $('set-notify').checked = !!snap.notificationsEnabled;
    $('set-login-item').checked = !!snap.openAtLogin;
    $('set-login-item').disabled = !snap.canAutoStart;
    $('set-login-note').textContent = snap.canAutoStart ? '' : 'This only works in the installed app on Windows or macOS.';
    $('set-account').textContent = (snap.employeeName ? snap.employeeName + ' ' : '') + (snap.loginName ? '(' + snap.loginName + ')' : '');
    $('set-storage').textContent = snap.secureStorage
      ? 'Your login is kept safely by Windows or macOS. Your password is never saved.'
      : 'Your login is not saved on this computer. You will need to log in each time you start the app. Your password is never saved.';
    $('set-version').textContent = snap.appVersion;
    $('btn-logout').disabled = busy.has('logout');
    $('btn-logout').textContent = busy.has('logout') ? 'Saving...' : 'Log out';
  }

  function renderLogin() {
    const first = !snap.serverUrl;
    $('login-title').textContent = first ? 'Welcome to BevyLoop' : 'Log in to BevyLoop';
    const server = $('in-server');
    if (!server.dataset.touched && snap.serverUrl) server.value = snap.serverUrl;
    if (!$('in-user').dataset.touched && snap.loginName) $('in-user').value = snap.loginName;
    $('storage-note').textContent = snap.secureStorage
      ? 'Your password is never saved. A safe login key is kept by Windows or macOS.'
      : 'Your password is never saved. This computer cannot keep a login key safely, so you will log in each time you start the app.';
    $('btn-login').disabled = busy.has('login');
    $('btn-login').textContent = busy.has('login') ? 'Saving...' : 'Sign in';
  }

  function showView() {
    const logged = snap && snap.loggedIn;
    $('view-login').hidden = !!logged;
    $('view-main').hidden = !logged || view !== 'main';
    $('view-settings').hidden = !logged || view !== 'settings';
    $('btn-settings').textContent = view === 'settings' ? 'Back' : 'Settings';
  }

  function renderAll() {
    if (!snap) return;
    renderHeader();
    renderBanners();
    showView();
    if (!snap.loggedIn) renderLogin();
    else if (view === 'settings') renderSettings();
    else renderMain();
  }

  // ------------------------------------------------------------ login form
  async function checkServerField() {
    const value = $('in-server').value;
    const hint = $('server-hint');
    if (!value.trim()) { setMsg(hint, null); $('insecure-box').hidden = true; insecureNeedsTick = false; return null; }
    const r = await api.checkUrl(value);
    if (!r.ok) { setMsg(hint, { kind: 'error', text: r.error }); $('insecure-box').hidden = true; insecureNeedsTick = false; return r; }
    setMsg(hint, null);
    insecureNeedsTick = !!r.insecure;
    $('insecure-box').hidden = !r.insecure;
    if (r.insecure) $('insecure-text').textContent = r.warning;
    return r;
  }

  async function submitLogin(event) {
    event.preventDefault();
    if (busy.has('login')) return;
    const msg = $('login-msg');
    const check = await checkServerField();
    if (!check || !check.ok) { setMsg(msg, { kind: 'error', text: check ? check.error : 'Please type the server address.' }); return; }
    if (check.insecure && !$('in-insecure').checked) {
      setMsg(msg, { kind: 'error', text: 'Please tick the box to confirm you want to use this connection.' });
      return;
    }
    busy.add('login');
    setMsg(msg, { kind: 'wait', text: 'Saving...' });
    renderLogin();
    let result;
    try {
      result = await api.login({
        serverUrl: $('in-server').value,
        username: $('in-user').value,
        password: $('in-pass').value,
        confirmInsecure: $('in-insecure').checked,
      });
    } catch (e) {
      result = { ok: false, message: 'Something went wrong. Please try again.' };
    }
    busy.delete('login');
    if (result.ok) {
      $('in-pass').value = '';
      setMsg(msg, null);
      view = 'main';
      renderAll();
      return;
    }
    setMsg(msg, { kind: 'error', text: result.message });
    renderLogin();
  }

  // ------------------------------------------------------------ wiring
  function onSnapshot(next) {
    snap = next;
    renderAll();
  }

  $('login-form').addEventListener('submit', submitLogin);
  $('in-server').addEventListener('input', (e) => { e.target.dataset.touched = '1'; checkServerField(); });
  $('in-server').addEventListener('blur', checkServerField);
  $('in-user').addEventListener('input', (e) => { e.target.dataset.touched = '1'; });
  $('btn-primary').addEventListener('click', primaryAction);
  $('btn-editor').addEventListener('click', async () => {
    const r = await api.openFullEditor();
    if (!r.ok) { primaryMsg = { kind: 'error', text: r.message }; renderAll(); }
  });
  $('btn-close').addEventListener('click', () => api.hideWindow());
  $('btn-pin').addEventListener('click', async () => {
    const r = await api.setPinned(!pinned);
    pinned = !!r.pinned;
    renderHeader();
  });
  $('btn-settings').addEventListener('click', () => { view = view === 'settings' ? 'main' : 'settings'; renderAll(); });
  $('btn-back').addEventListener('click', () => { view = 'main'; renderAll(); });
  $('set-notify').addEventListener('change', async (e) => {
    const r = await api.saveSettings({ notificationsEnabled: e.target.checked });
    setMsg($('set-msg'), r.ok ? { kind: 'ok', text: 'Saved.' } : { kind: 'error', text: r.message });
  });
  $('set-login-item').addEventListener('change', async (e) => {
    const r = await api.saveSettings({ openAtLogin: e.target.checked });
    setMsg($('set-msg'), r.ok ? { kind: 'ok', text: 'Saved.' } : { kind: 'error', text: r.message });
    if (!r.ok) e.target.checked = !e.target.checked;
  });
  $('btn-logout').addEventListener('click', async () => {
    busy.add('logout');
    renderSettings();
    await api.logout();
    busy.delete('logout');
    view = 'main';
    $('in-pass').value = '';
  });

  window.addEventListener('online', () => api.networkOnline());

  api.onSnapshot(onSnapshot);
  api.onNavigate((target) => {
    if (target === 'settings') view = 'settings';
    else { view = 'main'; if (target === 'update') { focusUpdateBox = true; renderedUpdatesKey = ''; } }
    renderAll();
  });

  setInterval(() => { if (snap && snap.loggedIn && view === 'main') renderTimer(); }, 1000);

  api.getSnapshot().then(onSnapshot);
})();
