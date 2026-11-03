import 'package:flutter_test/flutter_test.dart';
import 'package:devnira/models.dart';

void main() {
  const miner = Device(
    id: 'M',
    name: 'Nova',
    family: 'Nova',
    kind: 'miner',
    virtualSpeed: 400,
    virtualWatts: 1200,
    pricePaise: 100,
  );
  const gen = Device(
    id: 'G',
    name: 'Volt',
    family: 'Volt',
    kind: 'generator',
    virtualSpeed: 0,
    virtualWatts: 600,
    pricePaise: 100,
  );
  test('power limits speed and generator off stops mining', () {
    expect(
      PowerState.calculate(
        [miner, gen],
        [const OwnedDevice('m', 'M', true), const OwnedDevice('g', 'G', true)],
      ).speed,
      200,
    );
    expect(
      PowerState.calculate(
        [miner, gen],
        [const OwnedDevice('m', 'M', true), const OwnedDevice('g', 'G', false)],
      ).speed,
      0,
    );
    expect(
      PowerState.calculate(
        [miner, gen],
        [const OwnedDevice('m', 'M', false), const OwnedDevice('g', 'G', true)],
      ).speed,
      0,
    );
  });
  test('invalid catalog values fail closed', () {
    expect(
      () => Device.fromJson({...miner.toJson(), 'virtualWatts': 0}),
      throwsFormatException,
    );
    expect(
      () => Device.fromJson({...miner.toJson(), 'pricePaise': -1}),
      throwsFormatException,
    );
    expect(Device.fromJson(miner.toJson()).id, 'M');
  });
}
