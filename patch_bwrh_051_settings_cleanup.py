from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
control_text = control.read_text(encoding="utf-8")
if not re.search(r"^Version: 1\.1~exp2$", control_text, flags=re.M):
    raise SystemExit("expected BetterWiFi RH 1.1~exp2 base")
control_text = re.sub(r"^Version: 1\.1~exp2$", "Version: 1.1~exp3", control_text, count=1, flags=re.M)
control.write_text(control_text, encoding="utf-8")

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "1.1-exp2":
    raise SystemExit(f"expected prefs 1.1-exp2, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "1.1-exp3"
info["CFBundleVersion"] = "24"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

plist_path = root / "prefs/Resources/Root.plist"
plist = plistlib.loads(plist_path.read_bytes())
items = plist.get("items", [])
by_key = {item.get("key"): item for item in items if item.get("key")}
groups = {item.get("label"): item for item in items if item.get("cell") == "PSGroupCell"}

required_keys = [
    "enabled", "language", "showTools", "efficientMode", "extendedSignalHistory", "pullToRefresh",
    "showCurrentSummary", "qualityScore", "compactMode", "showScanAge", "showRSSI", "showSecurity",
    "showChannel", "showBand", "showBSSID", "showConnectedDetails", "detailsShowBSSID", "showVendorOUI",
    "detailsShowChannelWidth", "detailsShowIPv4", "detailsShowIPv6", "detailsShowRouter", "detailsShowDNS",
    "detailsShowPrivateAddress", "tapToCopy", "bandFilter", "networkTypeFilter", "minimumRSSIEnabled",
    "minimumRSSI", "openOnly", "unfilteredScan", "sortMode"
]
missing = [key for key in required_keys if key not in by_key]
if missing:
    raise SystemExit(f"missing preference keys: {missing}")

for label in ["BetterWiFi RH", "Diagnostics & battery", "Network information", "Connected network", "Advanced filters"]:
    if label not in groups:
        raise SystemExit(f"missing preference group: {label}")

main_group = dict(groups["BetterWiFi RH"])
main_group.pop("footerText", None)

monitor_group = dict(groups["Diagnostics & battery"])
monitor_group["label"] = "Monitoring & tools"

network_group = dict(groups["Network information"])
network_group["label"] = "Network list"
network_group["footerText"] = "Choose the information and presentation used in the Wi-Fi network list."

connected_group = dict(groups["Connected network"])

filters_group = dict(groups["Advanced filters"])
filters_group["label"] = "Filters & sorting"
filters_group["footerText"] = "Filters affect only the Wi-Fi list. The channel analyzer keeps the complete scan snapshot."

minimum_rssi = dict(by_key["minimumRSSI"])
minimum_rssi["validTitles"] = ["-95 dBm", "-90 dBm", "-85 dBm", "-80 dBm", "-75 dBm", "-70 dBm"]

sort_mode = dict(by_key["sortMode"])
sort_mode["validTitles"] = ["Original", "Signal", "Name", "Ch."]

plist["items"] = [
    main_group,
    by_key["enabled"], by_key["language"],

    monitor_group,
    by_key["showTools"], by_key["efficientMode"], by_key["extendedSignalHistory"], by_key["pullToRefresh"],

    network_group,
    by_key["showCurrentSummary"], by_key["qualityScore"], by_key["compactMode"], by_key["showScanAge"],
    by_key["showRSSI"], by_key["showSecurity"], by_key["showChannel"], by_key["showBand"], by_key["showBSSID"],

    connected_group,
    by_key["showConnectedDetails"], by_key["detailsShowBSSID"], by_key["showVendorOUI"],
    by_key["detailsShowChannelWidth"], by_key["detailsShowIPv4"], by_key["detailsShowIPv6"],
    by_key["detailsShowRouter"], by_key["detailsShowDNS"], by_key["detailsShowPrivateAddress"], by_key["tapToCopy"],

    filters_group,
    by_key["bandFilter"], by_key["networkTypeFilter"], by_key["minimumRSSIEnabled"], minimum_rssi,
    by_key["openOnly"], by_key["unfilteredScan"], sort_mode,
]
plist_path.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML, sort_keys=False))

strings_path = root / "prefs/Resources/es.lproj/Root.strings"
lines = strings_path.read_text(encoding="utf-8").splitlines()
obsolete_prefixes = (
    '"Advanced Wi-Fi controls for iOS 16 and RootHide. No background daemon is used."',
    '"BetterWiFi classic"',
    '"Classic BetterWiFi-style list behavior. Unfiltered scanning can reveal weaker access points but does not increase antenna power."',
    '"Diagnostics & battery"',
    '"Network information"',
    '"Advanced filters"',
    '"Choose the technical information shown next to Wi-Fi networks."',
    '"Filters are applied only to the Wi-Fi list. The channel analyzer keeps the complete scan snapshot."',
    '"Experimental 1.1"',
    '"Low-risk additions only. The quality score is derived from RSSI. These options use existing scan data or public system APIs and do not add a background daemon."',
    '"iOS"',
)
lines = [line for line in lines if not line.startswith(obsolete_prefixes)]
strings = "\n".join(lines).rstrip() + "\n"

new_strings = {
    "Monitoring & tools": "Monitorización y herramientas",
    "Network list": "Lista de redes",
    "Choose the information and presentation used in the Wi-Fi network list.": "Elige la información y la presentación usadas en la lista de redes Wi‑Fi.",
    "Filters & sorting": "Filtros y ordenación",
    "Filters affect only the Wi-Fi list. The channel analyzer keeps the complete scan snapshot.": "Los filtros afectan solo a la lista Wi‑Fi. El analizador de canales conserva la captura completa del escaneo.",
    "Original": "Original",
}
for english, spanish in new_strings.items():
    if f'"{english}" =' not in strings:
        strings += f'"{english}" = "{spanish}";\n'
strings_path.write_text(strings, encoding="utf-8")

controller_path = root / "prefs/BWRHRootListController.m"
controller = controller_path.read_text(encoding="utf-8")

old_filter_block = '''            if ([currentName caseInsensitiveCompare:@"Advanced filters"] == NSOrderedSame ||
                [currentName caseInsensitiveCompare:@"Filtros avanzados"] == NSOrderedSame) {
                insideAdvancedFilters = YES;
                specifier.name = @"Advanced filters";
                [specifier setProperty:@"Filters are applied only to the Wi-Fi list. The channel analyzer keeps the complete scan snapshot."
                                forKey:@"footerText"];
                continue;
            }
'''
new_filter_block = '''            if ([currentName caseInsensitiveCompare:@"Filters & sorting"] == NSOrderedSame ||
                [currentName caseInsensitiveCompare:@"Filtros y ordenación"] == NSOrderedSame) {
                insideAdvancedFilters = YES;
                specifier.name = @"Filters & sorting";
                [specifier setProperty:@"Filters affect only the Wi-Fi list. The channel analyzer keeps the complete scan snapshot."
                                forKey:@"footerText"];
                continue;
            }
'''
if old_filter_block not in controller:
    raise SystemExit("advanced filter localization block not found")
controller = controller.replace(old_filter_block, new_filter_block, 1)

classic_boundary = '''
            if ([currentName caseInsensitiveCompare:@"BetterWiFi classic"] == NSOrderedSame ||
                [currentName caseInsensitiveCompare:@"BetterWiFi clásico"] == NSOrderedSame) {
                insideAdvancedFilters = NO;
            }
'''
if classic_boundary not in controller:
    raise SystemExit("classic section boundary not found")
controller = controller.replace(classic_boundary, "\n", 1)

old_rssi_titles = 'BWRHSetPreferenceTitles(specifier, @[@"-95", @"-90", @"-85", @"-80", @"-75", @"-70"]);'
new_rssi_titles = 'BWRHSetPreferenceTitles(specifier, @[@"-95 dBm", @"-90 dBm", @"-85 dBm", @"-80 dBm", @"-75 dBm", @"-70 dBm"]);'
if old_rssi_titles not in controller:
    raise SystemExit("minimum RSSI titles anchor not found")
controller = controller.replace(old_rssi_titles, new_rssi_titles, 1)

old_sort_titles = 'BWRHSetPreferenceTitles(specifier, @[@"iOS", @"Signal", @"Name", @"Ch."]);'
new_sort_titles = 'BWRHSetPreferenceTitles(specifier, @[@"Original", @"Signal", @"Name", @"Ch."]);'
if old_sort_titles not in controller:
    raise SystemExit("sort titles anchor not found")
controller = controller.replace(old_sort_titles, new_sort_titles, 1)

controller_path.write_text(controller, encoding="utf-8")

for forbidden in [
    "Advanced Wi-Fi controls for iOS 16 and RootHide. No background daemon is used.",
    "Classic BetterWiFi-style list behavior. Unfiltered scanning can reveal weaker access points but does not increase antenna power.",
    "BetterWiFi classic",
]:
    for path in [plist_path, strings_path]:
        if forbidden in path.read_text(encoding="utf-8"):
            raise SystemExit(f"obsolete text remains in {path}: {forbidden}")

print("BetterWiFi RH 1.1~exp3 settings cleanup applied")
