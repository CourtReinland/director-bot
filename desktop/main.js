// Director-bot desktop shell.
//
// Spawns the Python backend (`director-bot serve`) on a free localhost port,
// waits for it to answer, then opens the dashboard in a BrowserWindow.
// `electron . --smoke` runs headless: spawn backend, health-poll, print
// "SMOKE OK", tear down, exit 0 (any failure exits 1).
'use strict';

const { app, BrowserWindow, Menu } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const nodeNet = require('net');
const os = require('os');
const path = require('path');

const SMOKE = process.argv.includes('--smoke');
const DEFAULT_BACKEND_BIN = path.join(
  __dirname, '..', '.venv', 'bin', 'director-bot');
const HEALTH_TIMEOUT_MS = 12000;

let backendChild = null;
let backendPort = null;
let mainWindow = null;
let tearingDown = false;

// Path to a frozen backend executable inside a packaged .app (future).
function packagedBackendBin() {
  return path.join(
    process.resourcesPath, 'backend', 'director-bot-backend', 'director-bot-backend');
}

function backendBin() {
  if (process.env.DIRECTOR_BOT_BACKEND_BIN) {
    return process.env.DIRECTOR_BOT_BACKEND_BIN;
  }
  if (app.isPackaged) return packagedBackendBin();
  return DEFAULT_BACKEND_BIN;
}

function backendAlive() {
  return backendChild !== null
    && backendChild.exitCode === null
    && backendChild.signalCode === null;
}

function findFreePort() {
  return new Promise((resolve, reject) => {
    const srv = nodeNet.createServer();
    srv.once('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

function spawnBackend(bin, port) {
  const env = { ...process.env };
  if (!env.DIRECTOR_BOT_HOME) {
    env.DIRECTOR_BOT_HOME = path.join(os.homedir(), '.director-bot');
  }
  const child = spawn(
    bin, ['serve', '--host', '127.0.0.1', '--port', String(port)],
    { env, stdio: ['ignore', 'pipe', 'pipe'] });
  child.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`));
  child.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`));
  child.on('error', (err) => console.error(`[backend] spawn error: ${err}`));
  child.on('exit', (code, signal) => {
    console.log(`[backend] exited code=${code} signal=${signal}`);
  });
  return child;
}

function healthOnce(port) {
  return new Promise((resolve) => {
    const req = http.get(
      { host: '127.0.0.1', port, path: '/api/health', timeout: 1500 },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

async function waitForBackend(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!backendAlive()) throw new Error('backend process exited during startup');
    if (await healthOnce(port)) return;
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error(`backend did not answer on 127.0.0.1:${port} within ${timeoutMs}ms`);
}

function terminateBackend() {
  return new Promise((resolve) => {
    if (!backendAlive()) { resolve(); return; }
    const child = backendChild;
    let done = false;
    const finish = () => { if (!done) { done = true; resolve(); } };
    const killTimer = setTimeout(() => {
      try { child.kill('SIGKILL'); } catch { /* already gone */ }
    }, 3000);
    const guardTimer = setTimeout(finish, 4000);
    killTimer.unref?.(); guardTimer.unref?.();
    child.once('exit', () => {
      clearTimeout(killTimer);
      clearTimeout(guardTimer);
      finish();
    });
    try { child.kill('SIGTERM'); } catch { clearTimeout(killTimer); finish(); }
  });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function showErrorWindow(title, lines) {
  const win = new BrowserWindow({
    width: 760, height: 460, backgroundColor: '#0c0d10',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event) => event.preventDefault());
  const body = lines.map((l) => `<p>${escapeHtml(l)}</p>`).join('\n');
  const html = [
    '<meta charset="utf-8">',
    '<style>body{background:#0c0d10;color:#eceae4;font:14px/1.6 ui-monospace,Menlo,monospace;',
    'padding:40px 48px}h1{font-size:18px;color:#d4a84b;letter-spacing:.08em}',
    'p{margin:10px 0;color:#8f8a80;white-space:pre-wrap}</style>',
    `<h1>${escapeHtml(title)}</h1>`,
    body,
  ].join('\n');
  win.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  return win;
}

function showBackendMissingWindow(bin) {
  if (app.isPackaged) {
    showErrorWindow('DIRECTOR-BOT BACKEND NOT FOUND', [
      `The bundled backend is missing from this app:\n  ${bin}`,
      'This copy of Director-bot appears incomplete. Rebuild, or set\n' +
        'DIRECTOR_BOT_BACKEND_BIN to a director-bot executable and relaunch.',
    ]);
    return;
  }
  showErrorWindow('DIRECTOR-BOT BACKEND NOT FOUND', [
    `Expected the backend CLI at:\n  ${bin}`,
    'To fix, either:',
    '1. Install the backend:\n   cd /Users/blue/Projects/director-bot && .venv/bin/pip install -e ".[web]"',
    '2. Or set DIRECTOR_BOT_BACKEND_BIN to your director-bot executable:\n' +
      '   DIRECTOR_BOT_BACKEND_BIN=/path/to/director-bot open -a "Director-bot"',
  ]);
}

function buildMenu() {
  const template = [
    { role: 'appMenu' },
    {
      label: 'File',
      submenu: [
        {
          label: 'Reload Dashboard',
          accelerator: 'CmdOrCtrl+R',
          click: () => { if (mainWindow) mainWindow.webContents.reload(); },
        },
        { type: 'separator' },
        { role: 'close' },
      ],
    },
    { role: 'editMenu' },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Navigate',
      submenu: [
        {
          label: 'Model View',
          accelerator: 'CmdOrCtrl+1',
          click: () => mainWindow?.webContents.executeJavaScript(
            "document.querySelector('[data-tab=model]')?.click()"),
        },
        {
          label: 'Projects',
          accelerator: 'CmdOrCtrl+2',
          click: () => mainWindow?.webContents.executeJavaScript(
            "document.querySelector('[data-tab=projects]')?.click()"),
        },
        {
          label: 'Canon',
          accelerator: 'CmdOrCtrl+3',
          click: () => mainWindow?.webContents.executeJavaScript(
            "document.querySelector('[data-tab=canon]')?.click()"),
        },
        {
          label: 'Decide',
          accelerator: 'CmdOrCtrl+4',
          click: () => mainWindow?.webContents.executeJavaScript(
            "document.querySelector('[data-tab=decide]')?.click()"),
        },
      ],
    },
    { role: 'windowMenu' },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1540,
    height: 980,
    minWidth: 1100,
    minHeight: 720,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0c0d10',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.on('closed', () => { mainWindow = null; });
  const appOrigin = `http://127.0.0.1:${backendPort}`;
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url !== appOrigin && !url.startsWith(`${appOrigin}/`)) {
      event.preventDefault();
    }
  });
  mainWindow.loadURL(`${appOrigin}/`);
}

async function startBackend() {
  const bin = backendBin();
  if (!fs.existsSync(bin)) {
    throw Object.assign(new Error(`backend binary not found at ${bin}`),
      { missingBin: bin });
  }
  backendPort = await findFreePort();
  backendChild = spawnBackend(bin, backendPort);
  await waitForBackend(backendPort, HEALTH_TIMEOUT_MS);
}

async function runSmoke() {
  try {
    await startBackend();
    console.log('SMOKE OK');
    await terminateBackend();
    app.exit(0);
  } catch (err) {
    console.error(`SMOKE FAIL: ${(err && err.message) || err}`);
    await terminateBackend();
    app.exit(1);
  }
}

async function runApp() {
  try {
    await startBackend();
  } catch (err) {
    if (err && err.missingBin) {
      showBackendMissingWindow(err.missingBin);
    } else {
      showErrorWindow('DIRECTOR-BOT BACKEND FAILED TO START', [
        String((err && err.message) || err),
        'Check the terminal output ([backend] lines) for the underlying error.',
        'Ensure pip install -e ".[web]" and that director-bot serve works alone.',
      ]);
    }
    return;
  }
  buildMenu();
  createWindow();
}

app.whenReady().then(() => (SMOKE ? runSmoke() : runApp()));

app.on('activate', () => {
  if (!SMOKE && backendPort !== null && BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('window-all-closed', () => {
  app.quit();
});

app.on('will-quit', (event) => {
  if (tearingDown || !backendAlive()) return;
  event.preventDefault();
  tearingDown = true;
  terminateBackend().then(() => app.quit());
});
