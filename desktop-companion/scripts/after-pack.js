'use strict';
// electron-builder afterPack hook (Windows only).
// The build runs with signAndEditExecutable: false (no Windows tools on the
// build machine), so electron-builder leaves Electron's default icon and
// version details in the exe. This writes our icon and the BevyLoop name into
// the exe using resedit, a pure JavaScript tool that needs no Windows.
const fs = require('node:fs');
const path = require('node:path');

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== 'win32') return;
  const ResEdit = require('resedit');
  const { productName } = context.packager.appInfo;
  const version = context.packager.appInfo.version;
  const exePath = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.exe`);
  const exe = ResEdit.NtExecutable.from(fs.readFileSync(exePath), { ignoreCert: true });
  const res = ResEdit.NtExecutableResource.from(exe);

  const iconFile = ResEdit.Data.IconFile.from(
    fs.readFileSync(path.join(__dirname, '..', 'assets', 'icon.ico'))
  );
  const groups = ResEdit.Resource.IconGroupEntry.fromEntries(res.entries);
  const groupId = groups.length ? groups[0].id : 1;
  const lang = groups.length ? groups[0].lang : 1033;
  ResEdit.Resource.IconGroupEntry.replaceIconsForResource(
    res.entries,
    groupId,
    lang,
    iconFile.icons.map((item) => item.data)
  );

  const [vi] = ResEdit.Resource.VersionInfo.fromEntries(res.entries);
  if (vi) {
    const parts = version.split('.').map((n) => parseInt(n, 10) || 0);
    while (parts.length < 4) parts.push(0);
    vi.setFileVersion(...parts);
    vi.setProductVersion(...parts);
    for (const t of vi.getAllLanguagesForStringValues()) {
      vi.setStringValues(t, {
        ProductName: productName,
        FileDescription: productName,
        CompanyName: 'Bevy Commerce',
        OriginalFilename: `${context.packager.appInfo.productFilename}.exe`,
        InternalName: productName,
        FileVersion: version,
        ProductVersion: version,
      });
    }
    vi.outputToResourceEntries(res.entries);
  }

  res.outputResource(exe);
  fs.writeFileSync(exePath, Buffer.from(exe.generate()));
  console.log(`  - afterPack: icon and version details written to ${path.basename(exePath)}`);
};
