import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'models.dart';

const liveMode = bool.fromEnvironment('LIVE', defaultValue: false);

class AppStore extends ChangeNotifier {
  final bool live;
  AppStore({this.live = liveMode});
  List<Device> catalog = [];
  List<OwnedDevice> fleet = [];
  List<Map<String, dynamic>> rounds = [], orders = [], audit = [];
  Map<String, dynamic> network = {};
  String? error, uid;
  String displayName = 'CHIRAGKUMAR', handle = 'chirag';
  String balance = '12,480.00';
  bool ready = false, admin = false, signedIn = false, online = true;
  final List<StreamSubscription<dynamic>> _streams = [];
  final List<StreamSubscription<dynamic>> _userStreams = [];
  StreamSubscription<User?>? _auth;
  SharedPreferences? _prefs;
  PowerState get power => PowerState.calculate(catalog, fleet);
  FirebaseFunctions get functions => FirebaseFunctions.instanceFor(
    region: const String.fromEnvironment(
      'FUNCTIONS_REGION',
      defaultValue: 'asia-south1',
    ),
  );

  Future<void> load() async {
    try {
      if (live) {
        await _loadLive();
      } else {
        await _loadDemo();
      }
      ready = true;
    } catch (_) {
      error = live
          ? 'Live setup is incomplete or unavailable. Check Firebase configuration and connection.'
          : 'Could not load the equipment catalog.';
    }
    notifyListeners();
  }

  Future<void> _loadDemo() async {
    _prefs = await SharedPreferences.getInstance();
    final bundled =
        jsonDecode(await rootBundle.loadString('assets/catalog.json'))
            as Map<String, dynamic>;
    final stored = _prefs!.getString('devnira_demo_catalog_v2');
    try {
      catalog =
          ((stored == null ? bundled['items'] : jsonDecode(stored)) as List)
              .map((x) => Device.fromJson(Map<String, dynamic>.from(x)))
              .toList();
    } catch (_) {
      catalog = (bundled['items'] as List)
          .map((x) => Device.fromJson(Map<String, dynamic>.from(x)))
          .toList();
    }
    final savedFleet = _prefs!.getString('devnira_demo_fleet_v2');
    if (savedFleet != null) {
      try {
        fleet = (jsonDecode(savedFleet) as List)
            .map((x) => OwnedDevice.fromJson(Map<String, dynamic>.from(x)))
            .toList();
      } catch (_) {
        fleet = [];
      }
    } else {
      final miners = catalog.where((x) => !x.generator).take(2).toList();
      fleet = [
        for (int i = 0; i < miners.length; i++)
          OwnedDevice('demo-m$i', miners[i].id, i == 0),
        OwnedDevice('demo-g1', catalog.firstWhere((x) => x.generator).id, true),
      ];
    }
    rounds = List.generate(
      6,
      (i) => {
        'height': 12846 - i,
        'handle': ['chirag', 'nova_07', 'aarya'][i % 3],
        'reward': '2,400',
        'status': 'Sample',
        'hash': 'Sample round — no chain transaction',
      },
    );
    network = {
      'supply': '2,000,000,000',
      'reward': '2,400',
      'virtualDifficulty': '1.00',
      'status': 'Demo only',
      'totalSpeed': 184000,
      'roundSeconds': 120,
    };
  }

  Future<void> _loadLive() async {
    const apiKey = String.fromEnvironment('FIREBASE_API_KEY');
    const appId = String.fromEnvironment('FIREBASE_APP_ID');
    const projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
    const sender = String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
    if ([apiKey, appId, projectId, sender].any((s) => s.isEmpty)) {
      throw StateError('Firebase config missing');
    }
    await Firebase.initializeApp(
      options: const FirebaseOptions(
        apiKey: apiKey,
        appId: appId,
        messagingSenderId: sender,
        projectId: projectId,
      ),
    );
    await FirebaseAppCheck.instance.activate(
      androidProvider: AndroidProvider.playIntegrity,
      webProvider: kIsWeb
          ? ReCaptchaV3Provider(
              const String.fromEnvironment('RECAPTCHA_SITE_KEY'),
            )
          : null,
    );
    FirebaseFirestore.instance.settings = const Settings(
      persistenceEnabled: false,
    );
    _streams.add(
      FirebaseFirestore.instance.collection('catalog').snapshots().listen((s) {
        catalog = s.docs
            .map((d) => Device.fromJson({...d.data(), 'id': d.id}))
            .toList();
        online = !s.metadata.isFromCache;
        notifyListeners();
      }, onError: _onError),
    );
    _streams.add(
      FirebaseFirestore.instance
          .collection('public_rounds')
          .orderBy('height', descending: true)
          .limit(50)
          .snapshots()
          .listen((s) {
            rounds = s.docs.map((d) => d.data()).toList();
            notifyListeners();
          }, onError: _onError),
    );
    _streams.add(
      FirebaseFirestore.instance.doc('public/network').snapshots().listen((s) {
        network = s.data() ?? {};
        notifyListeners();
      }, onError: _onError),
    );
    _auth = FirebaseAuth.instance.idTokenChanges().listen((user) async {
      for (final sub in _userStreams) {
        await sub.cancel();
      }
      _userStreams.clear();
      uid = user?.uid;
      signedIn = user != null;
      admin = false;
      fleet = [];
      orders = [];
      balance = '0.00';
      if (user != null) {
        try {
          final token = await user.getIdTokenResult();
          if (uid != user.uid) return;
          admin = token.claims?['admin'] == true;
          displayName =
              user.displayName ?? user.email?.split('@').first ?? 'Miner';
          handle = 'miner_${user.uid.substring(0, 6)}';
          _userStreams.add(
            FirebaseFirestore.instance
                .collection('users/${user.uid}/equipment')
                .snapshots()
                .listen((s) {
                  fleet = s.docs
                      .map(
                        (d) => OwnedDevice.fromJson({...d.data(), 'id': d.id}),
                      )
                      .toList();
                  online = !s.metadata.isFromCache;
                  notifyListeners();
                }, onError: _onError),
          );
          _userStreams.add(
            FirebaseFirestore.instance
                .collection('users/${user.uid}/orders')
                .orderBy('createdAt', descending: true)
                .limit(50)
                .snapshots()
                .listen((s) {
                  orders = s.docs
                      .map((d) => {...d.data(), 'id': d.id})
                      .toList();
                  notifyListeners();
                }, onError: _onError),
          );
          _userStreams.add(
            FirebaseFirestore.instance
                .doc('users/${user.uid}')
                .snapshots()
                .listen((s) {
                  final data = s.data();
                  handle = data?['handle'] as String? ?? handle;
                  balance = data?['balanceDisplay'] as String? ?? '0.00';
                  notifyListeners();
                }, onError: _onError),
          );
        } catch (_) {
          _onError(null);
        }
      }
      notifyListeners();
    });
  }

  void _onError(Object? _) {
    online = false;
    error = 'Connection unavailable. Live changes require internet.';
    notifyListeners();
  }

  Future<void> toggle(OwnedDevice owned, bool enabled) async {
    if (live) {
      if (!online || !signedIn) {
        throw StateError('Sign in and reconnect first.');
      }
      await functions.httpsCallable('toggleEquipment').call({
        'equipmentId': owned.id,
        'enabled': enabled,
      });
    } else {
      fleet = fleet
          .map((x) => x.id == owned.id ? x.toggle(enabled) : x)
          .toList();
      await _prefs?.setString(
        'devnira_demo_fleet_v2',
        jsonEncode(fleet.map((x) => x.toJson()).toList()),
      );
      notifyListeners();
    }
  }

  Future<void> saveDevice(Device device) async {
    Device.fromJson(device.toJson());
    if (live) {
      if (!online || !admin) {
        throw StateError('Administrator access and internet required.');
      }
      await functions.httpsCallable('saveCatalogDevice').call(device.toJson());
    } else {
      catalog = [...catalog.where((x) => x.id != device.id), device];
      final entry = {
        'action': 'Saved ${device.name}',
        'at': DateTime.now().toIso8601String(),
      };
      audit.insert(0, entry);
      await _prefs?.setString(
        'devnira_demo_catalog_v2',
        jsonEncode(catalog.map((x) => x.toJson()).toList()),
      );
      notifyListeners();
    }
  }

  Future<void> emailAuth(
    String email,
    String password, {
    bool create = false,
  }) async {
    if (!live) {
      throw StateError(
        'Demo mode. Authentication is available in a configured Live build.',
      );
    }
    if (create) {
      await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );
    } else {
      await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
    }
  }

  Future<void> googleAuth() async {
    if (!live) {
      throw StateError(
        'Demo mode. Google login needs your Firebase project configuration.',
      );
    }
    if (kIsWeb) {
      await FirebaseAuth.instance.signInWithPopup(GoogleAuthProvider());
      return;
    }
    final user = await GoogleSignIn(
      serverClientId:
          const String.fromEnvironment('GOOGLE_WEB_CLIENT_ID').isEmpty
          ? null
          : const String.fromEnvironment('GOOGLE_WEB_CLIENT_ID'),
    ).signIn();
    if (user == null) return;
    final auth = await user.authentication;
    await FirebaseAuth.instance.signInWithCredential(
      GoogleAuthProvider.credential(
        idToken: auth.idToken,
        accessToken: auth.accessToken,
      ),
    );
  }

  Future<void> resetPassword(String email) async {
    if (!live) {
      throw StateError(
        'Demo mode. Password reset needs Firebase configuration.',
      );
    }
    await FirebaseAuth.instance.sendPasswordResetEmail(email: email);
  }

  Future<void> signOut() async {
    if (live) {
      await FirebaseAuth.instance.signOut();
    }
  }

  Future<void> purchase(Device device) async {
    if (!live) {
      throw StateError(
        'Demo build: no money is charged and no purchase is made.',
      );
    }
    if (!signedIn) throw StateError('Sign in to continue.');
    await functions.httpsCallable('createOrder').call({'catalogId': device.id});
    // This release deliberately has no enabled payment provider. The server rejects
    // checkout until the merchant and crypto-related business model are approved.
  }

  Future<List<Map<String, dynamic>>> loadAudit() async {
    if (!live) return audit;
    if (!admin) throw StateError('Administrator access required.');
    final s = await FirebaseFirestore.instance
        .collection('audit')
        .orderBy('createdAt', descending: true)
        .limit(100)
        .get();
    return s.docs.map((d) => d.data()).toList();
  }

  @override
  void dispose() {
    _auth?.cancel();
    for (final s in [..._streams, ..._userStreams]) {
      s.cancel();
    }
    super.dispose();
  }
}
