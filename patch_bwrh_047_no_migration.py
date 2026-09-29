
from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")
control = root / "control"
text = control.read_text()

checks = {
    "Package": "com.betterwifirh.tweak.roothide",
    "Version": "0.3.15",
    "Architecture": "iphoneos-arm64e",
}
for key, value in checks.items():
    if not re.search(rf"^{re.escape(key)}: {re.escape(value)}$", text, flags=re.M):
        raise SystemExit(f"expected {key}: {value}")

text = re.sub(r"^Version:.*$", "Version: 0.3.16", text, count=1, flags=re.M)
text = re.sub(
    r"^Conflicts:.*$",
    "Conflicts: com.betterwifirh.tweak, com.betterwifirh.tweak.dopamine, com.betterwifirh.tweak.rootful",
    text,
    count=1,
    flags=re.M,
)
text = re.sub(r"^Breaks:.*$", "Breaks: com.betterwifirh.tweak (<< 0.3.16)", text, count=1, flags=re.M)
text = re.sub(r"^Replaces:.*$", "Replaces: com.betterwifirh.tweak (<< 0.3.16)", text, count=1, flags=re.M)
control.write_text(text)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "0.3.15":
    raise SystemExit(f"expected prefs 0.3.15, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "0.3.16"
info["CFBundleVersion"] = "19"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

print("BetterWiFi RH 0.3.16 no-migration packaging patch applied")

