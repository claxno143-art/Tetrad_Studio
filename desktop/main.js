// Tetrad Studio for Windows and macOS.
// Every tool is a plain HTML page loaded from file://. All windows share one session,
// so localStorage is shared live between tools, the same as the Linux version
// (the Reader's "From reading" set shows up in the List Trainer right away).
const { app, BrowserWindow, Menu, shell } = require('electron');
const path = require('path');

const TOOLS = {
  'suite':        { title: 'Tetrad Studio',        file: 'suite.html',        w: 720,  h: 560 },
  'reader':       { title: 'Russian Reader',   file: 'reader.html',       w: 1100, h: 860 },
  'list-trainer': { title: 'List Trainer',     file: 'list-trainer.html', w: 1100, h: 820 },
  'opi-tool':     { title: 'OPI Memory Tool',  file: 'opi-tool.html',     w: 1100, h: 860 },
  'opi-example':  { title: 'OPI Memory Tool: Worked Example', file: 'opi-example.html', w: 1100, h: 860 },
};
const open = {};   // tool key -> window

app.setName('Tetrad Studio');
if (process.platform === 'win32') app.setAppUserModelId('io.github.russianstudy.tetradstudio');

function openTool(key) {
  if (!TOOLS[key]) key = 'suite';
  const existing = open[key];
  if (existing && !existing.isDestroyed()) {
    if (existing.isMinimized()) existing.restore();
    existing.focus();
    return existing;
  }
  const t = TOOLS[key];
  const win = new BrowserWindow({
    width: t.w, height: t.h, minWidth: 560, minHeight: 480,
    title: t.title, show: false, backgroundColor: '#eef1f6',
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: { contextIsolation: true, sandbox: true, spellcheck: false },
  });
  open[key] = win;
  win.on('closed', () => { delete open[key]; });
  win.once('ready-to-show', () => win.show());
  win.on('page-title-updated', e => e.preventDefault());   // keep our window titles

  const wc = win.webContents;
  wc.on('will-navigate', (e, url) => {
    if (url.startsWith('launch:')) {          // buttons in the suite
      e.preventDefault();
      openTool(url.slice('launch:'.length));
      if (key === 'suite') setTimeout(() => { if (!win.isDestroyed()) win.close(); }, 300);
    } else if (/^https?:/.test(url)) {
      e.preventDefault(); shell.openExternal(url);
    } else if (url.startsWith('file:') && !url.includes(t.file)) {
      e.preventDefault();                     // tools never navigate to each other's files
    }
  });
  wc.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('launch:')) openTool(url.slice(7));
    else if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  win.loadFile(path.join(__dirname, 'app', t.file));
  return win;
}

function buildMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{ role: 'appMenu' }] : []),
    { label: 'Tools', submenu: [
      { label: 'Tetrad Studio home', accelerator: 'CmdOrCtrl+0', click: () => openTool('suite') },
      { label: 'Russian Reader', accelerator: 'CmdOrCtrl+1', click: () => openTool('reader') },
      { label: 'List Trainer', accelerator: 'CmdOrCtrl+2', click: () => openTool('list-trainer') },
      { label: 'OPI Memory Tool', accelerator: 'CmdOrCtrl+3', click: () => openTool('opi-tool') },
      { label: 'OPI Worked Example', accelerator: 'CmdOrCtrl+4', click: () => openTool('opi-example') },
      { type: 'separator' },
      isMac ? { role: 'close' } : { role: 'quit', label: 'Quit' },
    ] },
    { role: 'editMenu' },
    { label: 'View', submenu: [
      { role: 'reload' }, { type: 'separator' },
      { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' },
      { type: 'separator' }, { role: 'togglefullscreen' },
    ] },
    { role: 'windowMenu' },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// one running copy: a second launch just brings the suite forward
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const any = Object.values(open).find(w => !w.isDestroyed());
    if (any) { if (any.isMinimized()) any.restore(); any.focus(); } else openTool('suite');
  });
  app.whenReady().then(() => {
    buildMenu();
    openTool(process.argv.find(a => TOOLS[a]) || 'suite');
    app.on('activate', () => { if (!Object.keys(open).length) openTool('suite'); });  // macOS dock click
  });
  app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
}
