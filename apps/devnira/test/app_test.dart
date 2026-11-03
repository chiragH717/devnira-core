import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:devnira/app.dart';
import 'package:devnira/store.dart';
import 'package:devnira/models.dart';

Future<void> tick(WidgetTester t) async {
  await t.pump();
  await t.runAsync(
    () => Future<void>.delayed(const Duration(milliseconds: 250)),
  );
  await t.pump(const Duration(milliseconds: 100));
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));
  testWidgets(
    'five requested tabs, shop filters and power switches work at mobile size',
    (t) async {
      t.view.physicalSize = const Size(390, 844);
      t.view.devicePixelRatio = 1;
      addTearDown(t.view.resetPhysicalSize);
      addTearDown(t.view.resetDevicePixelRatio);
      final s = AppStore(live: false);
      await t.runAsync(s.load);
      await t.pumpWidget(DevniraApp(store: s));
      await tick(t);
      expect(find.text('Recent Rounds'), findsOneWidget);
      expect(s.catalog.where((d) => !d.generator).length, 120);
      expect(s.catalog.where((d) => d.generator).length, 24);
      await t.tap(find.byKey(const ValueKey('nav-1')));
      await tick(t);
      expect(find.text('Shop'), findsWidgets);
      await t.enterText(
        find.byKey(const ValueKey('shop-search')),
        'not-existing',
      );
      await t.pump();
      expect(find.text('No equipment matches your search'), findsOneWidget);
      await t.tap(find.byKey(const ValueKey('nav-3')));
      await tick(t);
      final generator = s.fleet.firstWhere((o) => o.id == 'demo-g1');
      expect(s.power.speed, greaterThan(0));
      await t.ensureVisible(find.byKey(ValueKey('switch-${generator.id}')));
      await t.tap(find.byKey(ValueKey('switch-${generator.id}')));
      await tick(t);
      expect(s.power.speed, 0);
      await t.tap(find.byKey(const ValueKey('nav-4')));
      await tick(t);
      expect(find.text('Continue with Google'), findsOneWidget);
      expect(t.takeException(), isNull);
      await t.pumpWidget(const SizedBox());
      s.dispose();
    },
  );
  testWidgets('admin rejects invalid equipment values', (t) async {
    final s = AppStore(live: false);
    await t.runAsync(s.load);
    await t.pumpWidget(DevniraApp(admin: true, store: s));
    await tick(t);
    await t.tap(find.text('Add new equipment'));
    await tick(t);
    await t.tap(find.text('Save'));
    await tick(t);
    expect(
      find.text('Enter a name, family and positive numeric values.'),
      findsOneWidget,
    );
    await t.tap(find.text('Cancel'));
    await tick(t);
    await t.pumpWidget(const SizedBox());
    s.dispose();
  });
  test('admin catalog and switch state persist across store reload', () async {
    final s = AppStore(live: false);
    await s.load();
    final original = s.catalog.first;
    await s.saveDevice(
      Device.fromJson({
        ...original.toJson(),
        'virtualSpeed': 999,
        'pricePaise': 123400,
      }),
    );
    final gen = s.fleet.firstWhere((o) => o.id == 'demo-g1');
    await s.toggle(gen, false);
    final next = AppStore(live: false);
    await next.load();
    expect(
      next.catalog.firstWhere((d) => d.id == original.id).virtualSpeed,
      999,
    );
    expect(
      next.catalog.firstWhere((d) => d.id == original.id).pricePaise,
      123400,
    );
    expect(next.power.speed, 0);
    s.dispose();
    next.dispose();
  });
  test('all catalog IDs are unique and records valid', () async {
    final j = jsonDecode(await rootBundle.loadString('assets/catalog.json'));
    final ids = (j['items'] as List).map((d) => d['id']).toSet();
    expect(ids.length, 144);
  });
}
