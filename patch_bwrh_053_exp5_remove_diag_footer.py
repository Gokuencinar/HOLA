from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
control_text = control.read_text(encoding="utf-8")
if not re.search(r"^Version: 1\.1~exp4$", control_text, flags=re.M):
    raise SystemExit("expected BetterWiFi RH 1.1~exp4 base")
control.write_text(
    re.sub(r"^Version: 1\.1~exp4$", "Version: 1.1~exp5", control_text, count=1, flags=re.M),
    encoding="utf-8",
)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "1.1-exp4":
    raise SystemExit(f"expected prefs 1.1-exp4, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "1.1-exp5"
info["CFBundleVersion"] = "26"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

tweak_path = root / "Tweak.xm"
tweak = tweak_path.read_text(encoding="utf-8")

old = '''- (NSString *)tableView:(UITableView *)tableView titleForFooterInSection:(NSInteger)section {
    return BWRHT(@"El diagnóstico se ejecuta solo bajo demanda. No deja pruebas de red ni procesos ejecutándose al salir de esta pantalla.",
                 @"Diagnostics run only on demand. No network tests or processes remain running after you leave this screen.");
}

'''
if old not in tweak:
    raise SystemExit("diagnostics footer anchor missing")
tweak = tweak.replace(old, "", 1)
tweak_path.write_text(tweak, encoding="utf-8")

for forbidden in [
    "El diagnóstico se ejecuta solo bajo demanda. No deja pruebas de red ni procesos ejecutándose al salir de esta pantalla.",
    "Diagnostics run only on demand. No network tests or processes remain running after you leave this screen.",
]:
    if forbidden in tweak:
        raise SystemExit(f"diagnostics footer text still present: {forbidden}")

print("BetterWiFi RH 1.1~exp5 diagnostics footer removed")
