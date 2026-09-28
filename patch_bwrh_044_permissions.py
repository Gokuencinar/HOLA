from pathlib import Path
import plistlib

root = Path("BetterWiFi-RH")

control = root / "control"
text = control.read_text()
if "Version: 0.3.12" not in text:
    raise SystemExit("expected BetterWiFi RH 0.3.12 control metadata")
control.write_text(text.replace("Version: 0.3.12", "Version: 0.3.13", 1))

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
info["CFBundleShortVersionString"] = "0.3.13"
info["CFBundleVersion"] = "16"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

print("BetterWiFi RH 0.3.13 packaging-permissions hotfix applied")
