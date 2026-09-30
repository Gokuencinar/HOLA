from pathlib import Path
import plistlib, re

root=Path("BetterWiFi-RH")

control=root/"control"
s=control.read_text(encoding="utf-8")
if not re.search(r"^Version: 1\.1~exp5$",s,re.M):
    raise SystemExit("expected 1.1~exp5 base")
control.write_text(re.sub(r"^Version: 1\.1~exp5$","Version: 1.1",s,count=1,flags=re.M),encoding="utf-8")

info_path=root/"prefs/Resources/Info.plist"
info=plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString")!="1.1-exp5":
    raise SystemExit(info.get("CFBundleShortVersionString"))
info["CFBundleShortVersionString"]="1.1"
info["CFBundleVersion"]="27"
info_path.write_bytes(plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False))

print("BetterWiFi RH stable 1.1 metadata applied")
