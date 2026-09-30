from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
s = control.read_text(encoding="utf-8")
if not re.search(r"^Version: 1\.1$", s, flags=re.M):
    raise SystemExit("expected BetterWiFi RH 1.1 stable base")
control.write_text(
    re.sub(r"^Version: 1\.1$", "Version: 1.1.1", s, count=1, flags=re.M),
    encoding="utf-8",
)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "1.1":
    raise SystemExit(f"expected prefs 1.1, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "1.1.1"
info["CFBundleVersion"] = "28"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

makefile = root / "Makefile"
mk = makefile.read_text(encoding="utf-8")
if "ARCHS = arm64e" not in mk:
    raise SystemExit("expected arm64e-only tweak Makefile")
mk = mk.replace("ARCHS = arm64e", "ARCHS = arm64 arm64e", 1)
makefile.write_text(mk, encoding="utf-8")

print("BetterWiFi RH 1.1.1 A11/arm64 RootHide compatibility patch applied")
