from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")
control = root / "control"
text = control.read_text()

for key, value in {
    "Package": "com.betterwifirh.tweak.roothide",
    "Version": "0.3.17",
    "Architecture": "iphoneos-arm64e",
}.items():
    if not re.search(rf"^{re.escape(key)}: {re.escape(value)}$", text, flags=re.M):
        raise SystemExit(f"expected {key}: {value}")

text = re.sub(r"^Version: 0\.3\.17$", "Version: 0.3.18", text, count=1, flags=re.M)
control.write_text(text)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "0.3.17":
    raise SystemExit(f"expected prefs 0.3.17, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "0.3.18"
info["CFBundleVersion"] = "21"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

print("BetterWiFi RH 0.3.18 generic Settings icon patch applied")
