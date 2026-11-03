import 'dart:math' as math;

class Device {
  final String id, name, family, kind;
  final int virtualSpeed, virtualWatts, pricePaise, tier, modelVariant;
  final bool published;
  const Device({
    required this.id,
    required this.name,
    required this.family,
    required this.kind,
    required this.virtualSpeed,
    required this.virtualWatts,
    required this.pricePaise,
    this.tier = 1,
    this.modelVariant = 1,
    this.published = true,
  });
  bool get generator => kind == 'generator';
  String get asset => generator
      ? 'generator-${(modelVariant - 1) % 2 + 1}.png'
      : 'miner-${(modelVariant - 1) % 3 + 1}.png';
  factory Device.fromJson(Map<String, dynamic> j) {
    final d = Device(
      id: j['id'] as String,
      name: j['name'] as String,
      family: j['family'] as String,
      kind: j['kind'] as String,
      virtualSpeed: (j['virtualSpeed'] as num).toInt(),
      virtualWatts: (j['virtualWatts'] as num).toInt(),
      pricePaise: (j['pricePaise'] as num).toInt(),
      tier: (j['tier'] as num?)?.toInt() ?? 1,
      modelVariant: (j['modelVariant'] as num?)?.toInt() ?? 1,
      published: j['published'] == true,
    );
    if (d.id.isEmpty ||
        d.name.trim().isEmpty ||
        !['miner', 'generator'].contains(d.kind) ||
        d.virtualSpeed < 0 ||
        d.virtualWatts <= 0 ||
        d.pricePaise <= 0 ||
        d.modelVariant < 1 ||
        (!d.generator && d.virtualSpeed == 0)) {
      throw const FormatException('Invalid equipment record');
    }
    return d;
  }
  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'family': family,
    'kind': kind,
    'virtualSpeed': virtualSpeed,
    'virtualWatts': virtualWatts,
    'pricePaise': pricePaise,
    'tier': tier,
    'modelVariant': modelVariant,
    'published': published,
  };
}

class OwnedDevice {
  final String id, catalogId;
  final bool enabled;
  const OwnedDevice(this.id, this.catalogId, this.enabled);
  factory OwnedDevice.fromJson(Map<String, dynamic> j) => OwnedDevice(
    j['id'] as String,
    j['catalogId'] as String,
    j['enabled'] == true,
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'catalogId': catalogId,
    'enabled': enabled,
  };
  OwnedDevice toggle(bool value) => OwnedDevice(id, catalogId, value);
}

class PowerState {
  final int supply, demand, ratedSpeed;
  const PowerState(this.supply, this.demand, this.ratedSpeed);
  double get factor => demand == 0 ? 0 : math.min(1, supply / demand);
  int get speed => (ratedSpeed * factor).floor();
  static PowerState calculate(List<Device> catalog, List<OwnedDevice> fleet) {
    final devices = {for (final d in catalog) d.id: d};
    int supply = 0, demand = 0, speed = 0;
    for (final o in fleet.where((x) => x.enabled)) {
      final d = devices[o.catalogId];
      if (d == null) continue;
      if (d.generator) {
        supply += d.virtualWatts;
      } else {
        demand += d.virtualWatts;
        speed += d.virtualSpeed;
      }
    }
    return PowerState(supply, demand, speed);
  }
}

String number(num value) => value
    .toStringAsFixed(0)
    .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (m) => '${m[1]},');
String money(int paise) => '₹${number(paise / 100)}';
