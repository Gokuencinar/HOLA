from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
control_text = control.read_text(encoding="utf-8")
if not re.search(r"^Version: 1\.1~exp3$", control_text, flags=re.M):
    raise SystemExit("expected BetterWiFi RH 1.1~exp3 base")
control.write_text(
    re.sub(r"^Version: 1\.1~exp3$", "Version: 1.1~exp4", control_text, count=1, flags=re.M),
    encoding="utf-8",
)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "1.1-exp3":
    raise SystemExit(f"expected prefs 1.1-exp3, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "1.1-exp4"
info["CFBundleVersion"] = "25"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

plist_path = root / "prefs/Resources/Root.plist"
plist = plistlib.loads(plist_path.read_bytes())
items = plist.get("items", [])
by_key = {item.get("key"): item for item in items if item.get("key")}

band = by_key.get("bandFilter")
sort_mode = by_key.get("sortMode")
if not band or not sort_mode:
    raise SystemExit("bandFilter/sortMode specifier missing")

band["validTitles"] = ["All", "2.4 GHz", "5 GHz", "6 GHz"]
sort_mode["label"] = "Sort networks by:"
plist_path.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML, sort_keys=False))

strings_path = root / "prefs/Resources/es.lproj/Root.strings"
strings = strings_path.read_text(encoding="utf-8")
if '"Sort networks by:"' not in strings:
    strings += '\n"Sort networks by:" = "Ordenar redes según:";\n'
strings_path.write_text(strings, encoding="utf-8")

controller_path = root / "prefs/BWRHRootListController.m"
controller = controller_path.read_text(encoding="utf-8")

old_band = 'BWRHSetPreferenceTitles(specifier, @[@"All", @"2.4", @"5", @"6"]);'
new_band = 'BWRHSetPreferenceTitles(specifier, @[@"All", @"2.4 GHz", @"5 GHz", @"6 GHz"]);'
if old_band not in controller:
    raise SystemExit("band title override anchor missing")
controller = controller.replace(old_band, new_band, 1)

old_sort_name = 'specifier.name = @"Sort networks";'
new_sort_name = 'specifier.name = @"Sort networks by:";'
if old_sort_name not in controller:
    raise SystemExit("sort label override anchor missing")
controller = controller.replace(old_sort_name, new_sort_name, 1)
controller_path.write_text(controller, encoding="utf-8")

tweak_path = root / "Tweak.xm"
tweak = tweak_path.read_text(encoding="utf-8")

old_empty = '''    if (section == 1 && self.rows5.count == 0) {
        return [NSString stringWithFormat:BWRHT(@"No se detectaron redes de 5 GHz. Fuente: %@ · registros: %ld · error MW: %ld. MobileWiFi se solicita sin límite de canal y con umbral -170 dBm.", @"No 5 GHz networks were detected. Source: %@ · records: %ld · MW error: %ld. MobileWiFi is requested with no channel limit and a -170 dBm threshold."), self.scanSource ?: @"—", (long)self.networks.count, (long)self.mobileWiFiScanError];
    }
    if (section == 1) return [NSString stringWithFormat:BWRHT(@"Fuente: %@ · %ld registros analizados.", @"Source: %@ · %ld records analyzed."), self.scanSource ?: @"—", (long)self.networks.count];
'''
new_empty = '''    if (section == 1 && self.rows5.count == 0) {
        return BWRHT(@"No se detectaron redes de 5 GHz.", @"No 5 GHz networks were detected.");
    }
    if (section == 1) return nil;
'''
if old_empty not in tweak:
    raise SystemExit("channel analyzer footer anchor missing")
tweak = tweak.replace(old_empty, new_empty, 1)
tweak_path.write_text(tweak, encoding="utf-8")

# Final checks: values remain unchanged; only presentation changes.
plist_check = plistlib.loads(plist_path.read_bytes())
check_by_key = {item.get("key"): item for item in plist_check.get("items", []) if item.get("key")}
if check_by_key["bandFilter"].get("validValues") != [0, 24, 5, 6]:
    raise SystemExit("band filter values changed unexpectedly")
if check_by_key["sortMode"].get("validValues") != [0, 1, 2, 3]:
    raise SystemExit("sort values changed unexpectedly")
if check_by_key["bandFilter"].get("validTitles") != ["All", "2.4 GHz", "5 GHz", "6 GHz"]:
    raise SystemExit("band labels not updated")
if check_by_key["sortMode"].get("label") != "Sort networks by:":
    raise SystemExit("sort label not updated")
if "Fuente: %@ · %ld registros analizados." in tweak or "Source: %@ · %ld records analyzed." in tweak:
    raise SystemExit("channel analyzer source footer still present")
if "Fuente: %@ · registros:" in tweak or "Source: %@ · records:" in tweak:
    raise SystemExit("channel analyzer debug footer still present")

print("BetterWiFi RH 1.1~exp4 UI cleanup applied")
