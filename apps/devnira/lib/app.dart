import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'models.dart';
import 'store.dart';

const navy = Color(0xFF050D22),
    panel = Color(0xFF101F3B),
    gold = Color(0xFFF1CA70),
    blue = Color(0xFF69B9FF),
    muted = Color(0xFFA0B1D1),
    green = Color(0xFF68F3AD);

void startDevnira({required bool admin}) {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(DevniraApp(admin: admin));
}

class DevniraApp extends StatefulWidget {
  final bool admin;
  final AppStore? store;
  const DevniraApp({super.key, this.admin = false, this.store});
  @override
  State<DevniraApp> createState() => _DevniraAppState();
}

class _DevniraAppState extends State<DevniraApp> {
  late final AppStore store;
  @override
  void initState() {
    super.initState();
    store = widget.store ?? AppStore();
    store.load();
  }

  @override
  void dispose() {
    if (widget.store == null) store.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: widget.admin ? 'Devnira Admin' : 'Devnira',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: navy,
      fontFamily: 'Roboto',
      colorScheme: const ColorScheme.dark(
        primary: gold,
        secondary: blue,
        surface: panel,
        onPrimary: navy,
        onSurface: Color(0xFFF3F6FF),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: navy,
        surfaceTintColor: Colors.transparent,
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: navy,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF294976)),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.all(Colors.white),
        trackColor: WidgetStateProperty.resolveWith(
          (s) => s.contains(WidgetState.selected)
              ? green
              : const Color(0xFF394B6A),
        ),
      ),
    ),
    home: AnimatedBuilder(
      animation: store,
      builder: (context, _) => Shell(store: store, admin: widget.admin),
    ),
  );
}

class Shell extends StatefulWidget {
  final AppStore store;
  final bool admin;
  const Shell({super.key, required this.store, required this.admin});
  @override
  State<Shell> createState() => _ShellState();
}

class _ShellState extends State<Shell> {
  int tab = 0;
  bool generators = false;
  String query = '', family = 'All';
  AppStore get s => widget.store;
  void notice(String message) {
    if (mounted)
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> act(Future<void> Function() action) async {
    try {
      await action();
    } catch (e) {
      notice(e.toString().replaceFirst('Bad state: ', ''));
    }
  }

  void page(String title, Widget content) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Padding(padding: const EdgeInsets.all(18), child: content),
          ),
        ),
      ),
    ),
  );
  void explorer() => page(
    'Devnira Explorer',
    ListView(
      children: [
        _label(s.live ? 'ON-CHAIN REWARD SETTLEMENTS' : 'DEMO EXPLORER', blue),
        const SizedBox(height: 12),
        const Text(
          'Reward rounds are operator-settled token distributions. Virtual equipment does not perform proof of work.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 16),
        ...s.rounds.map((r) => roundTile(r, detail: true)),
        if (s.rounds.isEmpty)
          const EmptyState('No settled rounds yet', Icons.travel_explore),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    if (s.error != null && !s.ready)
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.cloud_off, size: 48, color: gold),
                const SizedBox(height: 20),
                Text(s.error!, textAlign: TextAlign.center),
                const SizedBox(height: 14),
                const Text(
                  'No demo fallback is used by a Live build.',
                  style: TextStyle(color: muted),
                ),
              ],
            ),
          ),
        ),
      );
    if (!s.ready)
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (widget.admin && s.live && !s.admin)
      return Scaffold(
        appBar: AppBar(title: const Text('DEVNIRA ADMIN')),
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Icon(Icons.admin_panel_settings, size: 72, color: gold),
            const SizedBox(height: 20),
            Text(
              s.signedIn
                  ? 'Administrator access required'
                  : 'Administrator sign in',
              style: const TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 14),
            const Text(
              'Only accounts with a server-issued admin claim can manage this app.',
              style: TextStyle(color: muted),
            ),
            const SizedBox(height: 24),
            GoldButton('Sign in with email', () => authDialog()),
            TextButton(
              onPressed: () => act(s.googleAuth),
              child: const Text('Continue with Google'),
            ),
            if (s.signedIn)
              TextButton(
                onPressed: () => act(s.signOut),
                child: const Text('Sign out'),
              ),
          ],
        ),
      );
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 18,
        title: Row(
          children: [
            const Brand(size: 30),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                widget.admin ? 'DEVNIRA ADMIN' : 'DEVNIRA',
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFF10295A),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFF3862A6)),
              ),
              child: Text(
                s.live ? 'LIVE' : 'DEMO',
                style: const TextStyle(
                  fontSize: 9,
                  color: blue,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Column(
            children: [
              if (!s.live)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 18,
                    vertical: 7,
                  ),
                  color: gold.withValues(alpha: .07),
                  child: const Text(
                    'Design demo · sample balances · payments off',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: gold, fontSize: 11),
                  ),
                ),
              if (!s.online)
                Container(
                  color: Colors.red.shade900,
                  padding: const EdgeInsets.all(10),
                  child: const Text(
                    'INTERNET REQUIRED · Live actions unavailable',
                  ),
                ),
              Expanded(
                child: widget.admin
                    ? adminContent()
                    : ListView(
                        key: ValueKey('page-$tab'),
                        padding: const EdgeInsets.fromLTRB(18, 10, 18, 24),
                        children: [home, shop, setups, power, account][tab](),
                      ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: widget.admin
          ? null
          : SafeArea(
              top: false,
              child: Container(
                margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [panel, navy],
                  ),
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(color: const Color(0xFF2A4572)),
                ),
                child: Row(
                  children: List.generate(5, (i) {
                    final labels = [
                      'Home',
                      'Shop',
                      'Setups',
                      'Power',
                      'Account',
                    ];
                    final icons = [
                      Icons.home_outlined,
                      Icons.shopping_bag_outlined,
                      Icons.layers_outlined,
                      Icons.bolt_outlined,
                      Icons.person_outline,
                    ];
                    return Expanded(
                      child: Semantics(
                        selected: tab == i,
                        button: true,
                        label: labels[i],
                        child: InkWell(
                          key: ValueKey('nav-$i'),
                          onTap: () => setState(() => tab = i),
                          borderRadius: BorderRadius.circular(14),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 11),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  icons[i],
                                  color: tab == i ? gold : muted,
                                  size: 22,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  labels[i],
                                  style: TextStyle(
                                    color: tab == i ? gold : muted,
                                    fontSize: 10,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Container(
                                  width: 23,
                                  height: 2,
                                  color: tab == i ? gold : Colors.transparent,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  }),
                ),
              ),
            ),
    );
  }

  List<Widget> home() => [
    Panel(
      child: Row(
        children: [
          const Brand(size: 62, coin: true),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Balance',
                  style: TextStyle(color: muted, fontSize: 12),
                ),
                const SizedBox(height: 5),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    '${s.balance} DVN',
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: wallet,
            tooltip: 'Wallet',
            icon: const Icon(Icons.chevron_right),
          ),
        ],
      ),
    ),
    const SizedBox(height: 12),
    Row(
      children: [
        Expanded(
          child: Metric(
            'Virtual Speed',
            '${number(s.power.speed)} vH/s',
            Icons.bolt,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Countdown(live: s.live, network: s.network),
        ),
      ],
    ),
    const SizedBox(height: 10),
    Panel(
      padding: 12,
      child: Row(
        children: [
          const Icon(Icons.card_giftcard, color: gold, size: 20),
          const SizedBox(width: 10),
          const Expanded(
            child: Text('Initial Reward', style: TextStyle(fontSize: 12)),
          ),
          Text(
            '${s.network['reward'] ?? '2,400'} DVN',
            style: const TextStyle(color: gold, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    ),
    const SizedBox(height: 14),
    ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: AspectRatio(
        aspectRatio: 1.65,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.asset('assets/mining-room.png', fit: BoxFit.cover),
            if (s.power.speed > 0) const IgnorePointer(child: EnergyFlow()),
            Positioned(
              left: 12,
              bottom: 12,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: navy.withValues(alpha: .8),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  s.power.speed > 0
                      ? '●  MINING ROOM ACTIVE'
                      : '●  MINING ROOM IDLE',
                  style: TextStyle(
                    color: s.power.speed > 0 ? green : muted,
                    fontSize: 10,
                  ),
                ),
              ),
            ),
            Positioned(
              right: 8,
              top: 8,
              child: IconButton.filledTonal(
                onPressed: () => setState(() => tab = 2),
                tooltip: 'Manage mining room',
                icon: const Icon(Icons.tune, size: 19),
              ),
            ),
          ],
        ),
      ),
    ),
    const SizedBox(height: 16),
    Panel(
      child: Column(
        children: [
          Row(
            children: [
              const Expanded(
                child: Text(
                  'Recent Rounds',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              TextButton(
                onPressed: explorer,
                child: const Text(
                  'Explorer ↗',
                  style: TextStyle(color: blue, fontSize: 12),
                ),
              ),
            ],
          ),
          ...s.rounds.take(3).map((r) => roundTile(r)),
          if (s.rounds.isEmpty)
            const EmptyState('No rounds yet', Icons.view_in_ar),
        ],
      ),
    ),
    const SizedBox(height: 12),
    Text(
      s.live
          ? 'Virtual allocation difficulty: ${s.network['virtualDifficulty'] ?? '—'}'
          : '2B max supply · 120-second reward rounds',
      style: const TextStyle(color: muted, fontSize: 11),
    ),
  ];

  Widget roundTile(Map<String, dynamic> r, {bool detail = false}) => ListTile(
    dense: true,
    contentPadding: EdgeInsets.zero,
    leading: const Brand(size: 29, coin: true),
    title: Text(
      '@${r['handle'] ?? 'unknown'}',
      style: const TextStyle(fontSize: 13),
    ),
    subtitle: Text(
      'Round #${r['height']} · ${r['status'] ?? 'Pending'}',
      style: const TextStyle(fontSize: 10, color: muted),
    ),
    trailing: Text(
      '${r['reward']} DVN',
      style: const TextStyle(
        color: gold,
        fontSize: 12,
        fontWeight: FontWeight.w600,
      ),
    ),
    onTap: () => page(
      'Round #${r['height']}',
      ListView(
        children: [
          Text(
            '@${r['handle']}',
            style: const TextStyle(fontSize: 28, color: gold),
          ),
          const SizedBox(height: 20),
          Text('${r['reward']} DVN · ${r['status']}'),
          const SizedBox(height: 14),
          SelectableText(
            '${r['hash'] ?? 'Settlement transaction pending'}',
            style: const TextStyle(color: muted),
          ),
          const SizedBox(height: 20),
          if (s.live && r['txUrl'] is String)
            GoldButton(
              'View chain transaction',
              () => openUrl(r['txUrl'] as String),
            ),
          if (!s.live)
            const Text(
              'Sample data. This record is not an on-chain block.',
              style: TextStyle(color: muted),
            ),
        ],
      ),
    ),
  );

  List<Widget> shop() {
    final all = s.catalog
        .where((d) => d.generator == generators && d.published)
        .toList();
    final families = ['All', ...all.map((d) => d.family).toSet()];
    final visible = all
        .where(
          (d) =>
              (family == 'All' || d.family == family) &&
              d.name.toLowerCase().contains(query.toLowerCase()),
        )
        .toList();
    return [
      heading(
        'Shop',
        'Get virtual miners and generators for your mining room.',
      ),
      Container(
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: panel,
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: const Color(0xFF294976)),
        ),
        child: Row(
          children: [false, true]
              .map(
                (g) => Expanded(
                  child: InkWell(
                    onTap: () => setState(() {
                      generators = g;
                      family = 'All';
                    }),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 11),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(8),
                        gradient: g == generators ? goldGradient : null,
                      ),
                      child: Text(
                        '${g ? 'Generators' : 'Miners'}  ${s.catalog.where((d) => d.generator == g && d.published).length}',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: g == generators ? navy : muted,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      ),
      const SizedBox(height: 12),
      TextField(
        key: const ValueKey('shop-search'),
        onChanged: (v) => setState(() => query = v),
        decoration: const InputDecoration(
          hintText: 'Search equipment',
          prefixIcon: Icon(Icons.search, size: 20),
          isDense: true,
        ),
      ),
      const SizedBox(height: 10),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: families
              .map(
                (f) => Padding(
                  padding: const EdgeInsets.only(right: 7),
                  child: ChoiceChip(
                    label: Text(f, style: const TextStyle(fontSize: 11)),
                    selected: family == f,
                    onSelected: (_) => setState(() => family = f),
                  ),
                ),
              )
              .toList(),
        ),
      ),
      const SizedBox(height: 12),
      ...visible.map(
        (d) => Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Panel(
            padding: 12,
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      flex: 5,
                      child: Equipment(device: d, active: true, height: 148),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      flex: 4,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            d.name,
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            d.generator ? 'Virtual Generator' : 'Virtual Miner',
                            style: const TextStyle(color: muted, fontSize: 11),
                          ),
                          const SizedBox(height: 12),
                          if (!d.generator)
                            stat(
                              Icons.bolt,
                              '${number(d.virtualSpeed)} vH/s',
                              'Virtual speed',
                            ),
                          const SizedBox(height: 10),
                          stat(
                            Icons.power,
                            '${number(d.virtualWatts)} vW',
                            d.generator ? 'Capacity' : 'Power demand',
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const Divider(color: Color(0xFF28436C)),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        money(d.pricePaise),
                        style: const TextStyle(
                          color: gold,
                          fontSize: 19,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    GoldButton('Preview', () => deviceDialog(d), small: true),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
      if (visible.isEmpty)
        const EmptyState('No equipment matches your search', Icons.search_off),
    ];
  }

  List<Widget> setups() => [
    heading(
      'Your Mining Room',
      'Manage your virtual mining setups and devices.',
    ),
    if (s.power.demand > s.power.supply)
      const Padding(
        padding: EdgeInsets.only(bottom: 12),
        child: Panel(
          child: Text(
            'Power limited · enable more generators to reach full speed.',
            style: TextStyle(color: gold),
          ),
        ),
      ),
    ...fleetCards(false),
    if (!s.fleet.any(
      (o) => s.catalog.any((d) => d.id == o.catalogId && !d.generator),
    ))
      EmptyState(
        s.live
            ? 'No miners owned. Purchased equipment appears here.'
            : 'No demo miners',
        Icons.dns_outlined,
      ),
    const SizedBox(height: 12),
    GoldButton(
      'Explore miners',
      () => setState(() {
        generators = false;
        family = 'All';
        tab = 1;
      }),
    ),
  ];
  List<Widget> power() => [
    heading('Power Setups', 'Configure your virtual power and generators.'),
    Row(
      children: [
        Expanded(
          child: Metric(
            'Virtual Power Capacity',
            '${number(s.power.supply)} vW',
            Icons.bolt,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Metric(
            'Virtual Power Demand',
            '${number(s.power.demand)} vW',
            Icons.power,
          ),
        ),
      ],
    ),
    const SizedBox(height: 12),
    Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Virtual Energy Flow', style: TextStyle(fontSize: 11)),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(5),
            child: LinearProgressIndicator(
              value: s.power.supply == 0
                  ? 0
                  : math.min(1, s.power.demand / s.power.supply),
              minHeight: 8,
              color: Colors.cyanAccent,
              backgroundColor: navy,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${number(s.power.demand)} / ${number(s.power.supply)} vW',
            style: const TextStyle(color: blue, fontSize: 11),
          ),
        ],
      ),
    ),
    const SizedBox(height: 14),
    ...fleetCards(true),
    GoldButton(
      'Explore generators',
      () => setState(() {
        generators = true;
        family = 'All';
        tab = 1;
      }),
    ),
    const SizedBox(height: 12),
    const Text(
      'Virtual energy powers virtual equipment. No physical electricity is generated.',
      style: TextStyle(color: muted, fontSize: 11),
    ),
  ];
  List<Widget> fleetCards(bool generator) {
    final devices = {for (final d in s.catalog) d.id: d};
    return s.fleet.where((o) => devices[o.catalogId]?.generator == generator).map((
      o,
    ) {
      final d = devices[o.catalogId]!;
      final active = o.enabled && (generator || s.power.speed > 0);
      return Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Panel(
          padding: 12,
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    flex: 5,
                    child: Equipment(device: d, active: active, height: 165),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    flex: 4,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          d.name,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          generator ? 'Virtual Generator' : 'Virtual Miner',
                          style: const TextStyle(color: muted, fontSize: 11),
                        ),
                        const SizedBox(height: 10),
                        _label(
                          active
                              ? (generator ? '● ON' : '● RUNNING')
                              : (o.enabled ? 'NO POWER' : 'Ⅱ OFF'),
                          active ? green : muted,
                        ),
                        const SizedBox(height: 10),
                        stat(
                          generator ? Icons.bolt : Icons.speed,
                          generator
                              ? '${number(d.virtualWatts)} vW'
                              : '${number(o.enabled ? d.virtualSpeed * s.power.factor : 0)} vH/s',
                          generator ? 'Capacity' : 'Virtual speed',
                        ),
                        if (!generator) ...[
                          const SizedBox(height: 8),
                          stat(
                            Icons.power,
                            '${number(d.virtualWatts)} vW',
                            'Power',
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(color: Color(0xFF294976)),
              Row(
                children: [
                  Icon(Icons.circle, size: 8, color: active ? green : muted),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      'Status: ${active
                          ? (generator ? 'Generating (Virtual)' : 'Running')
                          : o.enabled
                          ? 'No power'
                          : 'Off'}',
                      style: const TextStyle(fontSize: 11),
                    ),
                  ),
                  Text(
                    o.enabled ? 'On' : 'Off',
                    style: const TextStyle(fontSize: 11),
                  ),
                  SizedBox(
                    height: 32,
                    child: Switch(
                      key: ValueKey('switch-${o.id}'),
                      value: o.enabled,
                      onChanged: (v) => act(() => s.toggle(o, v)),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }).toList();
  }

  List<Widget> account() => [
    const SizedBox(height: 15),
    Row(
      children: [
        Container(
          width: 73,
          height: 73,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: gold, width: 2),
            gradient: const RadialGradient(colors: [panel, navy]),
          ),
          child: Center(
            child: Text(
              s.displayName.isEmpty
                  ? 'D'
                  : s.displayName
                        .substring(0, math.min(2, s.displayName.length))
                        .toUpperCase(),
              style: const TextStyle(fontSize: 25),
            ),
          ),
        ),
        const SizedBox(width: 18),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                s.displayName,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 5),
              Text('@${s.handle}', style: const TextStyle(color: muted)),
            ],
          ),
        ),
      ],
    ),
    const SizedBox(height: 30),
    if (!s.signedIn) ...[
      FilledButton.icon(
        style: FilledButton.styleFrom(
          backgroundColor: Colors.white,
          foregroundColor: navy,
          padding: const EdgeInsets.all(14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
        onPressed: () => act(s.googleAuth),
        icon: const Icon(Icons.account_circle, color: Color(0xFF4285F4)),
        label: const Text('Continue with Google'),
      ),
      const SizedBox(height: 10),
      OutlinedButton.icon(
        onPressed: () => authDialog(),
        icon: const Icon(Icons.mail_outline),
        label: const Text('Sign in with email'),
      ),
      TextButton(
        onPressed: () => authDialog(reset: true),
        child: const Text('Forgot password?', style: TextStyle(color: blue)),
      ),
    ],
    const SizedBox(height: 18),
    accountTile(Icons.account_balance_wallet_outlined, 'Wallet', wallet),
    accountTile(
      Icons.inventory_2_outlined,
      'Order history',
      () => page(
        'Order history',
        ListView(
          children: [
            if (s.orders.isEmpty)
              const EmptyState('No purchases yet', Icons.receipt_long_outlined),
            ...s.orders.map(
              (o) => Panel(
                child: ListTile(
                  title: Text('${o['productName'] ?? o['catalogId']}'),
                  subtitle: Text('${o['status']} · ${o['id']}'),
                  trailing: Text(
                    money((o['amountPaise'] as num?)?.toInt() ?? 0),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    ),
    accountTile(
      Icons.shield_outlined,
      'Security',
      () => page(
        'Security',
        ListView(
          children: [
            const Panel(
              child: Text(
                'Passwords are handled by Firebase Authentication. Admin privileges are verified on the server. No seed phrases are requested by this app.',
              ),
            ),
            const SizedBox(height: 14),
            GoldButton('Reset password', () => authDialog(reset: true)),
            if (s.signedIn)
              TextButton(
                onPressed: () => act(s.signOut),
                child: const Text('Sign out'),
              ),
          ],
        ),
      ),
    ),
    accountTile(
      Icons.help_outline,
      'Help',
      () => page(
        'Help & information',
        ListView(
          children: const [
            Panel(
              child: Text(
                'Devnira uses purchased virtual equipment. It performs no physical GPU, ASIC or phone mining. Virtual speed determines app allocation, not blockchain consensus.',
              ),
            ),
            SizedBox(height: 14),
            Panel(
              child: Text(
                'Demo mode uses sample balances and equipment. Payments and token withdrawals are unavailable until live services are configured.',
              ),
            ),
            SizedBox(height: 14),
            Panel(
              child: Text(
                'No income or block win is guaranteed. Operating effects stop when power is off.',
              ),
            ),
          ],
        ),
      ),
    ),
    const SizedBox(height: 20),
    Text(
      s.live
          ? 'Devnira v0.2.0 · Live configuration'
          : 'Devnira v0.2.0 · Local design demo',
      style: const TextStyle(color: muted, fontSize: 11),
    ),
  ];
  Widget accountTile(IconData icon, String title, VoidCallback tap) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Panel(
      padding: 0,
      child: ListTile(
        leading: Icon(icon, color: gold),
        title: Text(title, style: const TextStyle(fontSize: 14)),
        trailing: const Icon(Icons.chevron_right, color: muted),
        onTap: tap,
      ),
    ),
  );
  void wallet() => page(
    'Wallet',
    ListView(
      children: [
        const Center(child: Brand(size: 130, coin: true)),
        const SizedBox(height: 22),
        Center(
          child: Text(
            '${s.balance} DVN',
            style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: 20),
        Panel(
          child: Text(
            s.live
                ? '${s.network['chainName'] ?? 'Chain configuration pending'}\nToken contract: ${s.network['tokenAddress'] ?? 'Not deployed'}'
                : 'Sample balance. No token has been minted or transferred.',
          ),
        ),
        const SizedBox(height: 18),
        const Text(
          'Withdrawals require a deployed contract and confirmed reward settlement.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 14),
        GoldButton('Reward explorer', explorer),
      ],
    ),
  );

  Future<void> authDialog({bool reset = false}) async {
    final email = TextEditingController(), password = TextEditingController();
    bool create = false, busy = false;
    String? error;
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, change) => AlertDialog(
          title: Text(
            reset
                ? 'Reset password'
                : create
                ? 'Create account'
                : 'Sign in',
          ),
          content: SizedBox(
            width: 370,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  decoration: const InputDecoration(labelText: 'Email'),
                ),
                if (!reset) ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: password,
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    decoration: const InputDecoration(labelText: 'Password'),
                  ),
                ],
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Text(error!, style: const TextStyle(color: gold)),
                  ),
                if (!reset)
                  TextButton(
                    onPressed: busy
                        ? null
                        : () => change(() => create = !create),
                    child: Text(
                      create
                          ? 'Already have an account? Sign in'
                          : 'Create a new account',
                    ),
                  ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: busy ? null : () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                          .hasMatch(email.text.trim())) {
                        change(() => error = 'Enter a valid email.');
                        return;
                      }
                      if (!reset && password.text.length < 8) {
                        change(() => error = 'Use at least 8 characters.');
                        return;
                      }
                      change(() {
                        busy = true;
                        error = null;
                      });
                      try {
                        if (reset) {
                          await s.resetPassword(email.text.trim());
                        } else {
                          await s.emailAuth(
                            email.text.trim(),
                            password.text,
                            create: create,
                          );
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                        if (reset)
                          notice(
                            'If this account exists, a reset email has been sent.',
                          );
                      } catch (e) {
                        if (ctx.mounted)
                          change(() {
                            busy = false;
                            error = e.toString().replaceFirst(
                              'Bad state: ',
                              '',
                            );
                          });
                      }
                    },
              child: Text(
                busy
                    ? 'Please wait…'
                    : reset
                    ? 'Send reset email'
                    : create
                    ? 'Create account'
                    : 'Sign in',
              ),
            ),
          ],
        ),
      ),
    );
    email.dispose();
    password.dispose();
  }

  Future<void> deviceDialog(Device d) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: panel,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                d.name,
                style: const TextStyle(
                  fontSize: 25,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Equipment(device: d, active: true, height: 220),
              Text(
                '${d.generator ? 'Capacity' : 'Speed'}: ${number(d.generator ? d.virtualWatts : d.virtualSpeed)} ${d.generator ? 'vW' : 'vH/s'}',
                style: const TextStyle(color: blue),
              ),
              const SizedBox(height: 12),
              Text(
                '${money(d.pricePaise)} INR',
                style: const TextStyle(color: gold, fontSize: 25),
              ),
              const SizedBox(height: 12),
              const Text(
                'Virtual equipment. No physical hardware is shipped. Rewards are variable and are not guaranteed.',
                textAlign: TextAlign.center,
                style: TextStyle(color: muted, fontSize: 12),
              ),
              const SizedBox(height: 20),
              GoldButton(s.live ? 'Purchase' : 'Payments off · Demo', () async {
                Navigator.pop(ctx);
                await act(() => s.purchase(d));
              }),
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Close'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget adminContent() {
    final all = s.catalog
        .where((d) => d.name.toLowerCase().contains(query.toLowerCase()))
        .toList();
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        heading(
          'Equipment Control',
          'Manage catalog, virtual speed, power and future sale prices.',
        ),
        Row(
          children: [
            Expanded(
              child: Metric(
                'Miners',
                '${s.catalog.where((d) => !d.generator).length}',
                Icons.dns_outlined,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Metric(
                'Generators',
                '${s.catalog.where((d) => d.generator).length}',
                Icons.bolt,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        GoldButton('Add new equipment', () => editDevice(null)),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () async {
            try {
              final entries = await s.loadAudit();
              if (!mounted) return;
              page(
                'Audit log',
                ListView(
                  children: [
                    if (entries.isEmpty)
                      const EmptyState('No changes recorded', Icons.history),
                    ...entries.map(
                      (e) => ListTile(
                        title: Text('${e['action']}'),
                        subtitle: Text('${e['at'] ?? e['createdAt']}'),
                      ),
                    ),
                  ],
                ),
              );
            } catch (_) {
              notice('Could not load audit log.');
            }
          },
          icon: const Icon(Icons.history),
          label: const Text('View audit log'),
        ),
        const SizedBox(height: 12),
        TextField(
          onChanged: (v) => setState(() => query = v),
          decoration: const InputDecoration(
            hintText: 'Search catalog',
            prefixIcon: Icon(Icons.search),
          ),
        ),
        const SizedBox(height: 16),
        ...all.map(
          (d) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Panel(
              padding: 6,
              child: ListTile(
                leading: SizedBox(
                  width: 54,
                  child: Image.asset('assets/${d.asset}', fit: BoxFit.contain),
                ),
                title: Text(d.name),
                subtitle: Text(
                  '${money(d.pricePaise)} · ${number(d.generator ? d.virtualWatts : d.virtualSpeed)} ${d.generator ? 'vW' : 'vH/s'}\n${d.published ? 'Published' : 'Hidden'}',
                  style: const TextStyle(color: muted, fontSize: 11),
                ),
                isThreeLine: true,
                trailing: const Icon(Icons.edit_outlined, color: gold),
                onTap: () => editDevice(d),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> editDevice(Device? d) async {
    final name = TextEditingController(text: d?.name ?? ''),
        speed = TextEditingController(text: '${d?.virtualSpeed ?? 100}'),
        watts = TextEditingController(text: '${d?.virtualWatts ?? 1200}'),
        price = TextEditingController(
          text: ((d?.pricePaise ?? 2499900) / 100).toStringAsFixed(2),
        ),
        familyC = TextEditingController(text: d?.family ?? 'Nova');
    bool gen = d?.generator ?? false,
        published = d?.published ?? false,
        busy = false;
    String? error;
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, change) => AlertDialog(
          title: Text(d == null ? 'Add equipment' : 'Edit ${d.name}'),
          content: SizedBox(
            width: 400,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: name,
                    decoration: const InputDecoration(
                      labelText: 'Equipment name',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: familyC,
                    decoration: const InputDecoration(labelText: 'Family'),
                  ),
                  const SizedBox(height: 12),
                  if (d == null)
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Generator'),
                      value: gen,
                      onChanged: (v) => change(() => gen = v),
                    ),
                  if (!gen)
                    TextField(
                      controller: speed,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Virtual speed (vH/s)',
                      ),
                    ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: watts,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: gen ? 'Capacity (vW)' : 'Demand (vW)',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: price,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(labelText: 'Price (INR)'),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Published'),
                    value: published,
                    onChanged: (v) => change(() => published = v),
                  ),
                  if (error != null)
                    Text(error!, style: const TextStyle(color: gold)),
                  const Text(
                    'Changes to speed and power affect all owned units. Price changes apply to future orders.',
                    style: TextStyle(color: muted, fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: busy ? null : () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      final w = int.tryParse(watts.text),
                          v = int.tryParse(speed.text),
                          p = double.tryParse(price.text);
                      if (name.text.trim().isEmpty ||
                          familyC.text.trim().isEmpty ||
                          w == null ||
                          w <= 0 ||
                          (!gen && (v == null || v <= 0)) ||
                          p == null ||
                          !p.isFinite ||
                          p <= 0 ||
                          p > 10000000) {
                        change(
                          () => error = 'Enter a name, family and positive numeric values.',
                        );
                        return;
                      }
                      final device = Device(
                        id:
                            d?.id ??
                            'custom-${DateTime.now().microsecondsSinceEpoch}',
                        name: name.text.trim(),
                        family: familyC.text.trim(),
                        kind: gen ? 'generator' : 'miner',
                        virtualSpeed: gen ? 0 : v!,
                        virtualWatts: w,
                        pricePaise: (p * 100).round(),
                        published: published,
                        modelVariant: d?.modelVariant ?? 1,
                        tier: d?.tier ?? 1,
                      );
                      change(() => busy = true);
                      try {
                        await s.saveDevice(device);
                        if (ctx.mounted) Navigator.pop(ctx);
                        notice(
                          'Equipment saved${s.live ? '' : ' in demo catalog'}.',
                        );
                      } catch (e) {
                        if (ctx.mounted)
                          change(() {
                            busy = false;
                            error = e.toString();
                          });
                      }
                    },
              child: Text(busy ? 'Saving…' : 'Save'),
            ),
          ],
        ),
      ),
    );
    for (final c in [name, speed, watts, price, familyC]) {
      c.dispose();
    }
  }

  Future<void> openUrl(String value) async {
    final uri = Uri.tryParse(value);
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      notice('No valid explorer URL configured.');
      return;
    }
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication))
      notice('Unable to open explorer.');
  }
}

Widget heading(String title, String subtitle) => Padding(
  padding: const EdgeInsets.only(bottom: 18),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
      ),
      const SizedBox(height: 6),
      Text(subtitle, style: const TextStyle(color: muted, fontSize: 12)),
    ],
  ),
);
Widget stat(IconData icon, String value, String label) => Row(
  children: [
    Icon(icon, color: gold, size: 20),
    const SizedBox(width: 6),
    Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
          Text(label, style: const TextStyle(fontSize: 10, color: muted)),
        ],
      ),
    ),
  ],
);
Widget _label(String text, Color color) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
  decoration: BoxDecoration(
    color: color.withValues(alpha: .13),
    borderRadius: BorderRadius.circular(20),
  ),
  child: Text(
    text,
    style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.w700),
  ),
);
const goldGradient = LinearGradient(
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
  colors: [Color(0xFFFFE6A0), Color(0xFFDDA83E)],
);

class GoldButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;
  final bool small;
  const GoldButton(this.label, this.onPressed, {super.key, this.small = false});
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      gradient: goldGradient,
      borderRadius: BorderRadius.circular(9),
    ),
    child: TextButton(
      style: TextButton.styleFrom(
        foregroundColor: navy,
        minimumSize: Size(small ? 90 : double.infinity, small ? 36 : 46),
        padding: EdgeInsets.symmetric(horizontal: small ? 17 : 22),
      ),
      onPressed: onPressed,
      child: Text(
        label,
        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
      ),
    ),
  );
}

class Panel extends StatelessWidget {
  final Widget child;
  final double padding;
  const Panel({super.key, required this.child, this.padding = 16});
  @override
  Widget build(BuildContext context) => Container(
    padding: EdgeInsets.all(padding),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(13),
      border: Border.all(color: const Color(0xFF2C497A)),
      gradient: const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF14294D), Color(0xFF0B172E)],
      ),
      boxShadow: [
        BoxShadow(color: Colors.blue.withValues(alpha: .05), blurRadius: 15),
      ],
    ),
    child: child,
  );
}

class Brand extends StatelessWidget {
  final double size;
  final bool coin;
  const Brand({super.key, this.size = 36, this.coin = false});
  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(coin ? size / 2 : 6),
    child: Image.asset(
      'assets/${coin ? 'coin' : 'app-icon'}.png',
      width: size,
      height: size,
      fit: BoxFit.cover,
    ),
  );
}

class Metric extends StatelessWidget {
  final String label, value;
  final IconData icon;
  const Metric(this.label, this.value, this.icon, {super.key});
  @override
  Widget build(BuildContext context) => Panel(
    padding: 12,
    child: Row(
      children: [
        Icon(icon, color: blue, size: 23),
        const SizedBox(width: 7),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(fontSize: 10, color: muted)),
              const SizedBox(height: 4),
              FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  value,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class Countdown extends StatefulWidget {
  final bool live;
  final Map<String, dynamic> network;
  const Countdown({super.key, required this.live, required this.network});
  @override
  State<Countdown> createState() => _CountdownState();
}

class _CountdownState extends State<Countdown> {
  Timer? timer;
  int left = 120;
  @override
  void initState() {
    super.initState();
    timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        if (!widget.live) {
          left = left <= 1 ? 120 : left - 1;
        } else {
          final next = widget.network['nextRoundAtMs'];
          left = next is num
              ? math.max(
                  0,
                  ((next - DateTime.now().millisecondsSinceEpoch) / 1000)
                      .ceil(),
                )
              : 0;
        }
      });
    });
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Metric(
    'Next Reward Round',
    widget.live && widget.network['nextRoundAtMs'] == null
        ? 'Pending'
        : '$left sec',
    Icons.schedule,
  );
}

class Equipment extends StatefulWidget {
  final Device device;
  final bool active;
  final double height;
  const Equipment({
    super.key,
    required this.device,
    required this.active,
    this.height = 160,
  });
  @override
  State<Equipment> createState() => _EquipmentState();
}

class _EquipmentState extends State<Equipment>
    with SingleTickerProviderStateMixin {
  late final AnimationController controller;
  void sync() {
    if (widget.active) {
      controller.repeat();
    } else {
      controller.stop();
    }
  }

  @override
  void initState() {
    super.initState();
    controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    );
    sync();
  }

  @override
  void didUpdateWidget(covariant Equipment oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.active != widget.active) sync();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SizedBox(
    height: widget.height,
    child: AnimatedBuilder(
      animation: controller,
      builder: (context, _) => Stack(
        fit: StackFit.expand,
        children: [
          ColorFiltered(
            colorFilter: widget.active
                ? const ColorFilter.mode(Colors.transparent, BlendMode.srcOver)
                : const ColorFilter.matrix([
                    .2126,
                    .7152,
                    .0722,
                    0,
                    0,
                    .2126,
                    .7152,
                    .0722,
                    0,
                    0,
                    .2126,
                    .7152,
                    .0722,
                    0,
                    0,
                    0,
                    0,
                    0,
                    1,
                    0,
                  ]),
            child: Opacity(
              opacity: widget.active ? 1 : .55,
              child: Image.asset(
                'assets/${widget.device.asset}',
                fit: BoxFit.contain,
              ),
            ),
          ),
          if (widget.active)
            Positioned(
              left: 8,
              right: 8,
              bottom: 5,
              child: Opacity(
                opacity: .2 + .35 * math.sin(controller.value * math.pi).abs(),
                child: Container(
                  height: 3,
                  decoration: BoxDecoration(
                    color: Colors.cyanAccent,
                    borderRadius: BorderRadius.circular(4),
                    boxShadow: const [
                      BoxShadow(
                        color: Colors.blue,
                        blurRadius: 14,
                        spreadRadius: 4,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          if (widget.active)
            Positioned(
              right: 5,
              top: 6,
              child: Transform.rotate(
                angle: controller.value * math.pi * 6,
                child: Icon(
                  widget.device.generator ? Icons.sync : Icons.settings,
                  color: blue.withValues(alpha: .65),
                  size: 18,
                ),
              ),
            ),
        ],
      ),
    ),
  );
}

class EnergyFlow extends StatefulWidget {
  const EnergyFlow({super.key});
  @override
  State<EnergyFlow> createState() => _EnergyFlowState();
}

class _EnergyFlowState extends State<EnergyFlow>
    with SingleTickerProviderStateMixin {
  late final AnimationController c;
  @override
  void initState() {
    super.initState();
    c = AnimationController(vsync: this, duration: const Duration(seconds: 3))
      ..repeat();
  }

  @override
  void dispose() {
    c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: c,
    builder: (context, _) => Align(
      alignment: Alignment(c.value * 2 - 1, .75),
      child: Container(
        width: 50,
        height: 2,
        decoration: const BoxDecoration(
          color: Colors.cyanAccent,
          boxShadow: [
            BoxShadow(color: Colors.blue, blurRadius: 14, spreadRadius: 5),
          ],
        ),
      ),
    ),
  );
}

class EmptyState extends StatelessWidget {
  final String message;
  final IconData icon;
  const EmptyState(this.message, this.icon, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 28),
    child: Column(
      children: [
        Icon(icon, size: 42, color: muted),
        const SizedBox(height: 14),
        Text(
          message,
          textAlign: TextAlign.center,
          style: const TextStyle(color: muted),
        ),
      ],
    ),
  );
}
