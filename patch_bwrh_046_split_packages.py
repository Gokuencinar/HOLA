from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
text = control.read_text()

expected = {
    "Package": "com.betterwifirh.tweak",
    "Version": "0.3.14",
    "Architecture": "iphoneos-arm64e",
}
for key, value in expected.items():
    if not re.search(rf"^{re.escape(key)}: {re.escape(value)}$", text, flags=re.M):
        raise SystemExit(f"expected {key}: {value}")

text = re.sub(r"^Package:.*$", "Package: com.betterwifirh.tweak.roothide", text, count=1, flags=re.M)
text = re.sub(r"^Version:.*$", "Version: 0.3.15", text, count=1, flags=re.M)
text = re.sub(r"^Name:.*$", "Name: BetterWiFi RH (RootHide)", text, count=1, flags=re.M)

for field in ("Conflicts", "Breaks", "Replaces"):
    text = re.sub(rf"^{field}:.*\n?", "", text, flags=re.M)

text = text.rstrip() + "\n"
text += "Conflicts: com.betterwifirh.tweak.dopamine, com.betterwifirh.tweak.rootful\n"
text += "Breaks: com.betterwifirh.tweak (<< 0.3.15)\n"
text += "Replaces: com.betterwifirh.tweak (<< 0.3.15)\n"
control.write_text(text)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "0.3.14":
    raise SystemExit(f"expected prefs 0.3.14, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "0.3.15"
info["CFBundleVersion"] = "18"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

print("BetterWiFi RH 0.3.15 split-package patch applied")
