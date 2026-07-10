'use strict';

// Ad-hoc re-sign extraResources Mach-O (backend) after electron-builder packs.
// electron-builder does not re-sign extraResources; Apple Silicon kills unsigned
// nested binaries.

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const MACHO_MAGICS = new Set([
  0xfeedface, 0xcefaedfe, 0xfeedfacf, 0xcffaedfe,
  0xcafebabe, 0xbebafeca, 0xcafebabf, 0xbfbafeca,
]);

function isMachO(file) {
  let fd;
  try {
    fd = fs.openSync(file, 'r');
    const buf = Buffer.alloc(4);
    const n = fs.readSync(fd, buf, 0, 4, 0);
    if (n < 4) return false;
    return MACHO_MAGICS.has(buf.readUInt32BE(0));
  } catch {
    return false;
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
}

function walkFilesDepthFirst(root) {
  const out = [];
  function recurse(dir) {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const ent of entries) {
      if (ent.isSymbolicLink()) continue;
      if (ent.isDirectory()) recurse(path.join(dir, ent.name));
    }
    for (const ent of entries) {
      if (ent.isSymbolicLink()) continue;
      if (ent.isFile()) out.push(path.join(dir, ent.name));
    }
  }
  recurse(root);
  return out;
}

function adhocSign(file) {
  execFileSync('codesign', ['--force', '-s', '-', '--timestamp=none', file],
    { stdio: ['ignore', 'ignore', 'pipe'] });
}

module.exports = async function afterPackSign(context) {
  const appOutDir = context.appOutDir;
  let appName = null;
  try {
    appName = fs.readdirSync(appOutDir).find((n) => n.endsWith('.app'));
  } catch (err) {
    console.error(`[afterpack-sign] cannot read appOutDir: ${err}`);
    return;
  }
  if (!appName) {
    console.error('[afterpack-sign] no .app found; skipping');
    return;
  }
  const resources = path.join(appOutDir, appName, 'Contents', 'Resources');
  const backendExe = path.join(
    resources, 'backend', 'director-bot-backend', 'director-bot-backend');
  const roots = [path.join(resources, 'backend')];

  let signed = 0;
  let failed = 0;
  const seen = new Set();
  const signOne = (file) => {
    if (seen.has(file)) return;
    seen.add(file);
    try {
      adhocSign(file);
      signed += 1;
    } catch (err) {
      failed += 1;
      console.error(`[afterpack-sign] failed ${file}: ${err}`);
    }
  };

  for (const root of roots) {
    if (!fs.existsSync(root)) {
      console.warn(`[afterpack-sign] missing: ${root}`);
      continue;
    }
    for (const file of walkFilesDepthFirst(root)) {
      if (isMachO(file)) signOne(file);
    }
  }
  if (fs.existsSync(backendExe)) signOne(backendExe);

  console.log(
    `[afterpack-sign] signed ${signed} Mach-O` +
    (failed ? `, ${failed} failed` : '') +
    ` under ${appName}`);
};
