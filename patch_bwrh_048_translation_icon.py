from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
control_text = control.read_text()
checks = {
    "Package": "com.betterwifirh.tweak.roothide",
    "Version": "0.3.16",
    "Architecture": "iphoneos-arm64e",
}
for key, value in checks.items():
    if not re.search(rf"^{re.escape(key)}: {re.escape(value)}$", control_text, flags=re.M):
        raise SystemExit(f"expected {key}: {value}")

controller = root / "prefs/BWRHRootListController.m"
s = controller.read_text()

helper_anchor = '''static NSArray *BWRHPreferenceTitlesForMode(NSArray *titles, NSInteger mode) {\n    if (![titles isKindOfClass:[NSArray class]] || mode == 0) return titles;\n    NSMutableArray *result = [NSMutableArray arrayWithCapacity:titles.count];\n    for (id title in titles) {\n        if ([title isKindOfClass:[NSString class]]) {\n            [result addObject:BWRHPreferenceStringForMode(title, mode)];\n        } else {\n            [result addObject:title];\n        }\n    }\n    return result;\n}\n'''
helper_replacement = helper_anchor + '''\nstatic void BWRHSetPreferenceTitles(PSSpecifier *specifier, NSArray *titles) {\n    if (![titles isKindOfClass:[NSArray class]]) return;\n\n    [specifier setProperty:titles forKey:@"validTitles"];\n\n    NSArray *values = [specifier propertyForKey:@"validValues"];\n    if (![values isKindOfClass:[NSArray class]] || values.count != titles.count) return;\n\n    // PSSegmentCell reads the cached value -> title map from PSSpecifier.\n    // PreferenceLoader may have localized that map before this controller\n    // sees the specifier, so changing only validTitles leaves stale labels.\n    NSMutableDictionary *titleDictionary = [NSMutableDictionary dictionaryWithCapacity:titles.count];\n    for (NSUInteger index = 0; index < titles.count; index++) {\n        id value = values[index];\n        id title = titles[index];\n        if ([value conformsToProtocol:@protocol(NSCopying)] && [title isKindOfClass:[NSString class]]) {\n            titleDictionary[value] = title;\n        }\n    }\n    specifier.titleDictionary = titleDictionary;\n}\n'''
if helper_anchor not in s:
    raise SystemExit("preference title helper anchor not found")
s = s.replace(helper_anchor, helper_replacement, 1)

old_generic_titles = '''        NSArray *titles = [specifier propertyForKey:@"validTitles"];\n        if ([titles isKindOfClass:[NSArray class]]) {\n            [specifier setProperty:BWRHPreferenceTitlesForMode(titles, mode) forKey:@"validTitles"];\n        }\n'''
new_generic_titles = '''        NSArray *titles = [specifier propertyForKey:@"validTitles"];\n        if ([titles isKindOfClass:[NSArray class]]) {\n            BWRHSetPreferenceTitles(specifier, BWRHPreferenceTitlesForMode(titles, mode));\n        }\n'''
if old_generic_titles not in s:
    raise SystemExit("generic validTitles update block not found")
s = s.replace(old_generic_titles, new_generic_titles, 1)

special_replacements = {
    '[specifier setProperty:@[@"All", @"2.4", @"5"] forKey:@"validTitles"];':
        'BWRHSetPreferenceTitles(specifier, @[@"All", @"2.4", @"5"]);',
    '[specifier setProperty:@[@"All", @"Known", @"New"] forKey:@"validTitles"];':
        'BWRHSetPreferenceTitles(specifier, @[@"All", @"Known", @"New"]);',
    '[specifier setProperty:@[@"-95", @"-90", @"-85", @"-80", @"-75", @"-70"] forKey:@"validTitles"];':
        'BWRHSetPreferenceTitles(specifier, @[@"-95", @"-90", @"-85", @"-80", @"-75", @"-70"]);',
    '[specifier setProperty:@[@"iOS", @"Signal", @"Name", @"Ch."] forKey:@"validTitles"];':
        'BWRHSetPreferenceTitles(specifier, @[@"iOS", @"Signal", @"Name", @"Ch."]);',
}
for old, new in special_replacements.items():
    if old not in s:
        raise SystemExit(f"advanced-filter title anchor not found: {old}")
    s = s.replace(old, new, 1)

controller.write_text(s)

# Use an explicit PreferenceLoader icon instead of relying on a fallback that
# differs between jailbreak/iOS combinations. A later build step provides the
# actual generic Wi-Fi icon.png inside the preference bundle.
entry_path = root / "layout/Library/PreferenceLoader/Preferences/BetterWiFiRH.plist"
entry = entry_path.read_text()
if 'icon = "icon.png";' not in entry:
    anchor = '        detail = BWRHRootListController;\n'
    if anchor not in entry:
        raise SystemExit("PreferenceLoader entry detail anchor not found")
    entry = entry.replace(anchor, anchor + '        icon = "icon.png";\n', 1)
entry_path.write_text(entry)

control_text = re.sub(r"^Version: 0\.3\.16$", "Version: 0.3.17", control_text, count=1, flags=re.M)
if "Version: 0.3.17" not in control_text:
    raise SystemExit("control version bump failed")
control.write_text(control_text)

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "0.3.16":
    raise SystemExit(f"expected prefs 0.3.16, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "0.3.17"
info["CFBundleVersion"] = "20"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

print("BetterWiFi RH 0.3.17 segmented-title translation + explicit Settings icon patch applied")
