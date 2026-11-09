// Put our icon and file details into Tetrad Studio.exe without needing Wine (resedit is pure JS).
const fs = require('fs'), path = require('path');
exports.default = async function (ctx) {
  if (ctx.electronPlatformName !== 'win32') return;
  const ResEdit = await import('resedit');
  const R = ResEdit.default || ResEdit;
  const exePath = path.join(ctx.appOutDir, 'Tetrad Studio.exe');
  const exe = R.NtExecutable.from(fs.readFileSync(exePath), { ignoreCert: true });
  const res = R.NtExecutableResource.from(exe);
  const ico = R.Data.IconFile.from(fs.readFileSync(path.join(__dirname, 'build', 'icon.ico')));
  const groups = R.Resource.IconGroupEntry.fromEntries(res.entries);
  const id = groups.length ? groups[0].id : 1, lang = groups.length ? groups[0].lang : 1033;
  R.Resource.IconGroupEntry.replaceIconsForResource(res.entries, id, lang, ico.icons.map(i => i.data));
  const vi = R.Resource.VersionInfo.fromEntries(res.entries)[0];
  if (vi) {
    const l = { lang: 1033, codepage: 1200 };
    vi.setStringValues(l, { FileDescription: 'Tetrad Studio', ProductName: 'Tetrad Studio', CompanyName: 'Tetrad Studio', OriginalFilename: 'Tetrad Studio.exe', InternalName: 'Tetrad Studio' });
    vi.setFileVersion(1, 5, 0, 0); vi.setProductVersion(1, 5, 0, 0);
    vi.outputToResourceEntries(res.entries);
  }
  res.outputResource(exe);
  fs.writeFileSync(exePath, Buffer.from(exe.generate()));
  console.log('  • set icon and version info on', path.basename(exePath));
};
