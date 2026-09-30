from pathlib import Path
import plistlib
import re

root = Path("BetterWiFi-RH")

control = root / "control"
s = control.read_text(encoding="utf-8")
if not re.search(r"^Version: 1\.1\.1$", s, flags=re.M):
    raise SystemExit("expected BetterWiFi RH 1.1.1 base")
control.write_text(re.sub(r"^Version: 1\.1\.1$", "Version: 1.2~exp1", s, count=1, flags=re.M), encoding="utf-8")

info_path = root / "prefs/Resources/Info.plist"
info = plistlib.loads(info_path.read_bytes())
if info.get("CFBundleShortVersionString") != "1.1.1":
    raise SystemExit(f"expected prefs 1.1.1, got {info.get('CFBundleShortVersionString')!r}")
info["CFBundleShortVersionString"] = "1.2-exp1"
info["CFBundleVersion"] = "29"
info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False))

tweak_path = root / "Tweak.xm"
tweak = tweak_path.read_text(encoding="utf-8")

old_tool = '''        [items addObject:@{ @"label": BWRHT(@"Monitor de señal", @"Signal monitor"), @"value": BWRHT(@"Gráfica en vivo", @"Live graph"), @"action": @"signal" }];
        [items addObject:@{ @"label": BWRHT(@"Analizador de canales", @"Channel analyzer"), @"value": BWRHT(@"Redes cercanas", @"Nearby networks"), @"action": @"channels" }];
        [items addObject:@{ @"label": BWRHT(@"Diagnóstico rápido", @"Quick diagnostics"), @"value": BWRHT(@"DNS e Internet", @"DNS & Internet"), @"action": @"diagnostics" }];
'''
new_tool = '''        [items addObject:@{ @"label": BWRHT(@"Monitor de señal", @"Signal monitor"), @"value": BWRHT(@"Gráfica en vivo", @"Live graph"), @"action": @"signal" }];
        [items addObject:@{ @"label": BWRHT(@"Analizador de canales", @"Channel analyzer"), @"value": BWRHT(@"Redes cercanas", @"Nearby networks"), @"action": @"channels" }];
        [items addObject:@{ @"label": BWRHT(@"Topología de red", @"Network topology"), @"value": BWRHT(@"Mesh, APs y roaming", @"Mesh, APs & roaming"), @"action": @"topology" }];
        [items addObject:@{ @"label": BWRHT(@"Diagnóstico rápido", @"Quick diagnostics"), @"value": BWRHT(@"DNS e Internet", @"DNS & Internet"), @"action": @"diagnostics" }];
'''
if old_tool not in tweak:
    raise SystemExit("tool-row anchor missing")
tweak = tweak.replace(old_tool, new_tool, 1)

controller_code = r'''
#pragma mark - Network topology / mesh analysis

static NSString *BWRHCanonicalBSSID(NSString *bssid) {
    if (!bssid.length) return @"";
    return [[bssid stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]] uppercaseString];
}

static id BWRHTopologyCurrentNetwork(id airportController, id currentNetwork) {
    if (!currentNetwork) return nil;
    NSArray *snapshot = BWRHLatestScanNetworks(airportController);
    NSString *bssid = BWRHCanonicalBSSID(BWRHBSSID(currentNetwork));
    unsigned long long uid = BWRHMsgUnsignedLongLong(currentNetwork, @"uniqueIdentifier", 0);

    for (id candidate in snapshot) {
        NSString *candidateBSSID = BWRHCanonicalBSSID(BWRHBSSID(candidate));
        if (bssid.length && [candidateBSSID isEqualToString:bssid]) return candidate;
        unsigned long long cuid = BWRHMsgUnsignedLongLong(candidate, @"uniqueIdentifier", 0);
        if (uid && cuid && uid == cuid) return candidate;
        SEL eqSel = NSSelectorFromString(@"isEquivalentRecord:");
        if ([currentNetwork respondsToSelector:eqSel] && ((BOOL (*)(id, SEL, id))objc_msgSend)(currentNetwork, eqSel, candidate)) return candidate;
    }
    return currentNetwork;
}

static NSArray *BWRHSameSSIDAccessPoints(id airportController, id currentNetwork) {
    currentNetwork = BWRHTopologyCurrentNetwork(airportController, currentNetwork);
    NSString *ssid = BWRHNetworkSSID(currentNetwork);
    if (!ssid.length) return @[];

    NSMutableArray *candidates = [NSMutableArray arrayWithArray:BWRHLatestScanNetworks(airportController) ?: @[]];
    if (currentNetwork) [candidates addObject:currentNetwork];

    NSMutableDictionary<NSString *, id> *deduped = [NSMutableDictionary dictionary];
    for (id candidate in candidates) {
        NSString *candidateSSID = BWRHNetworkSSID(candidate) ?: @"";
        if (![candidateSSID isEqualToString:ssid]) continue;
        NSString *bssid = BWRHCanonicalBSSID(BWRHBSSID(candidate));
        NSString *key = bssid.length ? bssid : @"__unknown_bssid__";
        id previous = deduped[key];
        long long rssi = BWRHNetworkRSSI(candidate);
        long long previousRSSI = BWRHNetworkRSSI(previous);
        if (!previous || (rssi != LLONG_MIN && (previousRSSI == LLONG_MIN || rssi > previousRSSI))) deduped[key] = candidate;
    }

    return [deduped.allValues sortedArrayUsingComparator:^NSComparisonResult(id a, id b) {
        long long arssi = BWRHNetworkRSSI(a);
        long long brssi = BWRHNetworkRSSI(b);
        if (arssi == brssi) return [BWRHCanonicalBSSID(BWRHBSSID(a)) compare:BWRHCanonicalBSSID(BWRHBSSID(b))];
        if (arssi == LLONG_MIN) return NSOrderedDescending;
        if (brssi == LLONG_MIN) return NSOrderedAscending;
        return arssi > brssi ? NSOrderedAscending : NSOrderedDescending;
    }];
}

static NSString *BWRHJoinedBands(NSArray *accessPoints) {
    NSMutableOrderedSet<NSString *> *bands = [NSMutableOrderedSet orderedSet];
    for (id network in accessPoints) {
        NSString *band = BWRHBandDescription(network);
        if (band.length) [bands addObject:band];
    }
    return [[bands array] componentsJoinedByString:@", "];
}

static NSString *BWRHJoinedChannels(NSArray *accessPoints) {
    NSMutableOrderedSet<NSNumber *> *channels = [NSMutableOrderedSet orderedSet];
    for (id network in accessPoints) {
        NSNumber *channel = BWRHChannelNumber(network);
        if (channel) [channels addObject:channel];
    }
    NSArray<NSNumber *> *sorted = [[channels array] sortedArrayUsingSelector:@selector(compare:)];
    NSMutableArray<NSString *> *strings = [NSMutableArray arrayWithCapacity:sorted.count];
    for (NSNumber *channel in sorted) [strings addObject:channel.stringValue];
    return [strings componentsJoinedByString:@", "];
}

static NSInteger BWRHVisibleNetworksOnCurrentChannel(id airportController, id currentNetwork) {
    NSNumber *currentChannel = BWRHChannelNumber(currentNetwork);
    NSString *currentBand = BWRHBandDescription(currentNetwork);
    if (!currentChannel) return 0;

    NSMutableSet<NSString *> *seen = [NSMutableSet set];
    for (id candidate in BWRHLatestScanNetworks(airportController)) {
        NSNumber *channel = BWRHChannelNumber(candidate);
        if (!channel || channel.integerValue != currentChannel.integerValue) continue;
        NSString *band = BWRHBandDescription(candidate);
        if (currentBand.length && band.length && ![band isEqualToString:currentBand]) continue;
        NSString *bssid = BWRHCanonicalBSSID(BWRHBSSID(candidate));
        NSString *key = bssid.length ? bssid : [NSString stringWithFormat:@"%@-%@", BWRHNetworkSSID(candidate) ?: @"", channel];
        [seen addObject:key];
    }
    return (NSInteger)seen.count;
}

@interface BWRHNetworkTopologyController : UITableViewController
@property (nonatomic, weak) UIViewController *airportController;
@property (nonatomic, strong) id currentNetwork;
@property (nonatomic, copy) NSArray<NSDictionary *> *summaryRows;
@property (nonatomic, copy) NSArray *accessPoints;
@property (nonatomic) BOOL refreshScheduled;
- (instancetype)initWithAirportController:(UIViewController *)airport network:(id)network;
@end

@implementation BWRHNetworkTopologyController

- (instancetype)initWithAirportController:(UIViewController *)airport network:(id)network {
    if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
        _airportController = airport;
        _currentNetwork = network;
        _summaryRows = @[];
        _accessPoints = @[];
        self.title = BWRHT(@"Topología de red", @"Network topology");
    }
    return self;
}

- (void)viewDidLoad {
    [super viewDidLoad];
    self.navigationItem.rightBarButtonItem = [[UIBarButtonItem alloc] initWithTitle:BWRHT(@"Actualizar", @"Refresh") style:UIBarButtonItemStylePlain target:self action:@selector(bwrh_refreshTopology)];
    [self rebuildAnalysis];
}

- (void)viewWillAppear:(BOOL)animated {
    [super viewWillAppear:animated];
    [self rebuildAnalysis];
    if (!self.refreshScheduled) {
        self.refreshScheduled = YES;
        BWRHRequestFreshScan(self.airportController);
        __weak typeof(self) weakSelf = self;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.1 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
            weakSelf.refreshScheduled = NO;
            [weakSelf rebuildAnalysis];
        });
    }
}

- (void)bwrh_refreshTopology {
    BWRHRequestFreshScan(self.airportController);
    [self rebuildAnalysis];
    __weak typeof(self) weakSelf = self;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.1 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [weakSelf rebuildAnalysis];
    });
}

- (void)rebuildAnalysis {
    id current = BWRHTopologyCurrentNetwork(self.airportController, self.currentNetwork);
    NSArray *aps = BWRHSameSSIDAccessPoints(self.airportController, current);
    self.accessPoints = aps ?: @[];

    NSMutableArray<NSDictionary *> *rows = [NSMutableArray array];
    void (^add)(NSString *, NSString *) = ^(NSString *label, NSString *value) {
        if (value.length) [rows addObject:@{ @"label": label, @"value": value }];
    };

    add(@"SSID", BWRHNetworkSSID(current));

    NSUInteger apCount = aps.count;
    NSString *topology = nil;
    if (apCount >= 2) topology = BWRHT(@"Posible mesh / multi‑AP", @"Possible mesh / multi-AP");
    else if (apCount == 1) topology = BWRHT(@"Un punto de acceso visible", @"One visible access point");
    else topology = BWRHT(@"Sin datos suficientes", @"Not enough data");
    add(BWRHT(@"Topología", @"Topology"), topology);
    add(BWRHT(@"Puntos de acceso", @"Access points"), [NSString stringWithFormat:@"%lu", (unsigned long)apCount]);

    NSString *bands = BWRHJoinedBands(aps);
    add(BWRHT(@"Bandas del SSID", @"SSID bands"), bands);
    add(BWRHT(@"Canales del SSID", @"SSID channels"), BWRHJoinedChannels(aps));

    NSUInteger bandCount = bands.length ? [bands componentsSeparatedByString:@", "].count : 0;
    if (bandCount > 1) add(@"Band steering", BWRHT(@"Posible · SSID multibanda", @"Possible · multi-band SSID"));

    NSMutableSet<NSString *> *ouis = [NSMutableSet set];
    for (id ap in aps) {
        NSString *oui = BWRHOUIForBSSID(BWRHBSSID(ap));
        if (oui.length) [ouis addObject:oui];
    }
    if (ouis.count) add(BWRHT(@"Grupos OUI", @"OUI groups"), [NSString stringWithFormat:@"%lu", (unsigned long)ouis.count]);

    NSString *currentBSSID = BWRHCanonicalBSSID(BWRHBSSID(current));
    if (currentBSSID.length) add(BWRHT(@"AP conectado", @"Connected AP"), currentBSSID);

    long long currentRSSI = BWRHLiveRSSIForAirport(self.airportController, current);
    id bestAlternate = nil;
    for (id ap in aps) {
        NSString *candidateBSSID = BWRHCanonicalBSSID(BWRHBSSID(ap));
        if (currentBSSID.length && [candidateBSSID isEqualToString:currentBSSID]) continue;
        if (!currentBSSID.length && ap == current) continue;
        if (BWRHNetworkRSSI(ap) == LLONG_MIN) continue;
        bestAlternate = ap;
        break;
    }

    if (bestAlternate) {
        long long alternateRSSI = BWRHNetworkRSSI(bestAlternate);
        NSString *altBSSID = BWRHCanonicalBSSID(BWRHBSSID(bestAlternate));
        NSMutableArray<NSString *> *parts = [NSMutableArray array];
        if (altBSSID.length) [parts addObject:altBSSID];
        [parts addObject:[NSString stringWithFormat:@"%lld dBm", alternateRSSI]];
        NSNumber *channel = BWRHChannelNumber(bestAlternate);
        if (channel) [parts addObject:[NSString stringWithFormat:@"Ch %@", channel]];
        NSString *band = BWRHBandDescription(bestAlternate);
        if (band.length) [parts addObject:band];
        add(BWRHT(@"Mejor AP alternativo", @"Best alternate AP"), [parts componentsJoinedByString:@" · "]);

        if (currentRSSI != LLONG_MIN) {
            long long delta = alternateRSSI - currentRSSI;
            if (delta >= 8) {
                add(BWRHT(@"Sugerencia de roaming", @"Roaming hint"), [NSString stringWithFormat:BWRHT(@"AP alternativo +%lld dB más fuerte", @"Alternate AP is +%lld dB stronger"), delta]);
            } else {
                add(BWRHT(@"Sugerencia de roaming", @"Roaming hint"), BWRHT(@"El AP actual está entre los más fuertes", @"Current AP is among the strongest"));
            }
        }
    } else if (apCount > 0) {
        add(BWRHT(@"Sugerencia de roaming", @"Roaming hint"), BWRHT(@"No hay AP alternativo visible", @"No alternate AP visible"));
    }

    NSInteger currentChannelVisible = BWRHVisibleNetworksOnCurrentChannel(self.airportController, current);
    if (currentChannelVisible > 0) add(BWRHT(@"APs visibles en el canal actual", @"Visible APs on current channel"), [NSString stringWithFormat:@"%ld", (long)currentChannelVisible]);
    add(BWRHT(@"Antigüedad del escaneo", @"Scan age"), BWRHLastScanAgeDescription());

    self.summaryRows = rows;
    [self.tableView reloadData];
}

- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView { return 2; }

- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section {
    return section == 0 ? self.summaryRows.count : self.accessPoints.count;
}

- (NSString *)tableView:(UITableView *)tableView titleForHeaderInSection:(NSInteger)section {
    return section == 0 ? BWRHT(@"Análisis avanzado", @"Advanced analysis") : BWRHT(@"Puntos de acceso del mismo SSID", @"Access points with same SSID");
}

- (NSString *)tableView:(UITableView *)tableView titleForFooterInSection:(NSInteger)section {
    if (section != 0) return nil;
    return BWRHT(@"La detección de mesh es heurística. Varios BSSID con el mismo SSID también pueden pertenecer a extensores o redes empresariales. BetterWiFi no fuerza el roaming.",
                 @"Mesh detection is heuristic. Multiple BSSIDs sharing one SSID can also be extenders or enterprise access points. BetterWiFi never forces roaming.");
}

- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)indexPath {
    if (indexPath.section == 0) {
        UITableViewCell *cell = [tableView dequeueReusableCellWithIdentifier:@"BWRHTopologySummary"];
        if (!cell) cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleValue1 reuseIdentifier:@"BWRHTopologySummary"];
        NSDictionary *row = self.summaryRows[indexPath.row];
        cell.textLabel.text = row[@"label"];
        cell.detailTextLabel.text = row[@"value"];
        cell.detailTextLabel.adjustsFontSizeToFitWidth = YES;
        cell.detailTextLabel.minimumScaleFactor = 0.55;
        cell.selectionStyle = BWRHBool(@"tapToCopy", YES) ? UITableViewCellSelectionStyleDefault : UITableViewCellSelectionStyleNone;
        cell.accessoryType = UITableViewCellAccessoryNone;
        return cell;
    }

    UITableViewCell *cell = [tableView dequeueReusableCellWithIdentifier:@"BWRHTopologyAP"];
    if (!cell) cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle reuseIdentifier:@"BWRHTopologyAP"];
    id ap = self.accessPoints[indexPath.row];
    NSString *bssid = BWRHCanonicalBSSID(BWRHBSSID(ap));
    cell.textLabel.text = bssid.length ? bssid : [NSString stringWithFormat:BWRHT(@"Punto de acceso %ld", @"Access point %ld"), (long)indexPath.row + 1];

    NSMutableArray<NSString *> *parts = [NSMutableArray array];
    long long rssi = BWRHNetworkRSSI(ap);
    if (rssi != LLONG_MIN) [parts addObject:[NSString stringWithFormat:@"%lld dBm", rssi]];
    NSNumber *channel = BWRHChannelNumber(ap);
    if (channel) [parts addObject:[NSString stringWithFormat:@"Ch %@", channel]];
    NSString *band = BWRHBandDescription(ap);
    if (band.length) [parts addObject:band];
    NSString *security = BWRHSecurityDescription(ap);
    if (security.length) [parts addObject:security];
    cell.detailTextLabel.text = [parts componentsJoinedByString:@" · "];
    cell.detailTextLabel.adjustsFontSizeToFitWidth = YES;
    cell.detailTextLabel.minimumScaleFactor = 0.55;

    NSString *currentBSSID = BWRHCanonicalBSSID(BWRHBSSID(BWRHTopologyCurrentNetwork(self.airportController, self.currentNetwork)));
    cell.accessoryType = (currentBSSID.length && [bssid isEqualToString:currentBSSID]) ? UITableViewCellAccessoryCheckmark : UITableViewCellAccessoryNone;
    cell.selectionStyle = bssid.length && BWRHBool(@"tapToCopy", YES) ? UITableViewCellSelectionStyleDefault : UITableViewCellSelectionStyleNone;
    return cell;
}

- (void)tableView:(UITableView *)tableView didSelectRowAtIndexPath:(NSIndexPath *)indexPath {
    [tableView deselectRowAtIndexPath:indexPath animated:YES];
    if (!BWRHBool(@"tapToCopy", YES)) return;
    NSString *value = nil;
    if (indexPath.section == 0) value = self.summaryRows[indexPath.row][@"value"];
    else value = BWRHCanonicalBSSID(BWRHBSSID(self.accessPoints[indexPath.row]));
    if (!value.length) return;
    UIPasteboard.generalPasteboard.string = value;
    UITableViewCell *cell = [tableView cellForRowAtIndexPath:indexPath];
    UITableViewCellAccessoryType oldType = cell.accessoryType;
    cell.accessoryType = UITableViewCellAccessoryCheckmark;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        if ([tableView cellForRowAtIndexPath:indexPath] == cell) cell.accessoryType = oldType;
    });
}

@end

'''

anchor = "#pragma mark - Quick diagnostics\n"
if anchor not in tweak:
    raise SystemExit("quick diagnostics anchor missing")
tweak = tweak.replace(anchor, controller_code + anchor, 1)

old_action = '''    } else if ([action isEqualToString:@"channels"]) {
        destination = [[BWRHChannelAnalyzerController alloc] initWithAirportController:self.airportController currentNetwork:network];
    } else if ([action isEqualToString:@"diagnostics"]) {
        destination = [[BWRHDiagnosticsController alloc] initWithNetwork:network config:BWRHMsgObject(self.sourceController, @"config")];
    }
'''
new_action = '''    } else if ([action isEqualToString:@"channels"]) {
        destination = [[BWRHChannelAnalyzerController alloc] initWithAirportController:self.airportController currentNetwork:network];
    } else if ([action isEqualToString:@"topology"]) {
        destination = [[BWRHNetworkTopologyController alloc] initWithAirportController:self.airportController network:network];
    } else if ([action isEqualToString:@"diagnostics"]) {
        destination = [[BWRHDiagnosticsController alloc] initWithNetwork:network config:BWRHMsgObject(self.sourceController, @"config")];
    }
'''
if old_action not in tweak:
    raise SystemExit("action anchor missing")
tweak = tweak.replace(old_action, new_action, 1)
tweak = tweak.replace("BetterWiFi RH 1.1 experimental diagnostic", "BetterWiFi RH 1.2 experimental diagnostic", 1)

tweak_path.write_text(tweak, encoding="utf-8")

for required in [
    "BWRHNetworkTopologyController",
    "Possible mesh / multi-AP",
    "Mesh detection is heuristic",
    '@"topology"',
    "Visible APs on current channel",
    "Band steering",
    "Best alternate AP",
]:
    if required not in tweak:
        raise SystemExit(f"missing advanced topology feature: {required}")

print("BetterWiFi RH 1.2~exp1 advanced topology analysis applied")
