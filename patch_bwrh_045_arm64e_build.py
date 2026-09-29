from pathlib import Path
import plistlib

root = Path("BetterWiFi-RH")

control = root / "control"
text = control.read_text()
if "Version: 0.3.13" not in text:
    raise SystemExit("expected BetterWiFi RH 0.3.13 control metadata")
control.write_text(text.replace("Version: 0.3.13", "Version: 0.3.14", 1))

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "0.3.13":
    raise SystemExit(f"expected prefs 0.3.13, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "0.3.14"
info["CFBundleVersion"] = "17"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

print("BetterWiFi RH 0.3.14 clean-build/arm64e validation patch applied")
