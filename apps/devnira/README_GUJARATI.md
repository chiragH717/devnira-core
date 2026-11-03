# Devnira User + Admin — v0.2

આ project નવી virtual-equipment app માટે છે. જૂની devnira-core chain, logo અને websiteના codeમાં ફેરફાર નથી.
આ app માટે અલગ 2B-supply EVM tokenનો source છે. કોઈ mainnet contract deploy કર્યો નથી.

## Android apps

- User: `com.devnira.app` — Home, Shop, Setups, Power, Account, reward explorer.
- Admin: `com.devnira.admin` — અલગ APK; catalog add/edit, price, speed, power, publish, audit.
- Gold/Blue icon અને coin મૂળ uploaded images છે.
- 120 miners + 24 generatorsના અલગ catalog records છે; ત્રણ miner અને બે generator visual families છે.
- Realistic machinery assets, active light/flow effects અને OFF grayscale state છે. આ actual rendered fan video નથી.
- Demoમાં local device switches અને admin catalog changes restart પછી પણ રહે છે.
- અલગ phonesમાં Demo data sync નથી થતો. Configured Firebase Live buildમાં catalog streams sync કરે છે.

## Copy-paste local checks

Flutter 3.47.9, Java 17, Android SDK, Node 20 જરૂરી.

```bash
flutter pub get
flutter analyze --no-fatal-infos
flutter test
npm ci --prefix backend
npm test --prefix backend
npm ci --prefix contracts
npm test --prefix contracts
flutter build apk --release --flavor player --target lib/main.dart --dart-define=LIVE=false
flutter build apk --release --flavor admin --target lib/main_admin.dart --dart-define=LIVE=false
```

આ APKs demo છે અને debug certificateથી sign થાય છે. Store માટે private release signing configuration બદલવી જરૂરી છે.
GitHub Actions ઉપર બંને APKs અલગ artifactમાં મળે છે. Build success એટલે Android compilation + tests; real device, Google login કે mainnet acceptance નહીં.

## Live configuration બાકી

1. પોતાનું Firebase project, બે Android app registrations, SHA-1/SHA-256 signing fingerprints અને OAuth web client ID.
2. Google અને Email/Password providers enable કરવા.
3. Firebase App Check સાથે apps register કરવી; Play Integrity production signing identity જરૂરી છે.
4. Functions + Firestore rules deploy, admin custom claim પોતાના trusted operator દ્વારા આપવો. UIમાંથી role આપવાનો રસ્તો નથી.
5. Catalog seed શરૂઆતમાં બધા draft/hidden રાખે છે. Admin કિંમત અને stats review કર્યા પછી publish કરે.
6. Approved merchant/payment providerનું actual integration અને tested webhook fulfillment હજી બાકી છે. Razorpay live checkout disabled છે.
7. Chain ID, RPC, explorer domain, owner/operator PUBLIC addresses અને audited deployed token contract.
8. Server reward allocation, fraud controls, independent fairness/randomness, wallet proof of ownership, receipt-to-entitlement fulfillment અને finality indexerનું production integration.
9. Domain name, support email અને privacy policy.

Private keys, seed phrases અથવા payment secrets chatમાં મોકલશો નહીં.

## Token protocol

8 decimals; maximum 2,000,000,000 DVN; first reward 2,400 DVN; minimum 120 seconds between operator-settled reward rounds.
No premine. New deployment starts paused. Owner uses two-step ownership transfer and appoints a reward operator.
Reward curve is the original package's proposed smooth decay:

`issued(n) = CAP * n * INITIAL / (CAP - INITIAL + n * INITIAL)`

`reward(n) = issued(n) - issued(n - 1)`

આ Pearl coinના exact verified emission rules નથી. Productionમાં આ proposal મંજૂર અને audit કર્યા પછી deploy કરવાનું.
Rewards are paid directly to a recipient by contract minting; a public handle hash and allocation digest are logged.
The contract enforces timing, replay prevention, authority and cap. It DOES NOT prove a fair recipient selection or implement physical PoW.
120 seconds are reward rounds, not an EVM chain's block time. App virtual difficulty must never be presented as native network difficulty.

## Payments

Razorpay terms prohibit crypto-related activity: https://razorpay.com/terms/
No real order, charge or entitlement is created by this release. Payment domain utilities/tests are preparation, not a deployed webhook.

## Assets

`assets/app-icon.png`, `assets/coin.png`: supplied unchanged.
`miner-1.png`–`miner-3.png`, `generator-1.png`–`generator-2.png`, `mining-room.png`: built-in Imagegen machinery atlas, cropped into six cells for app use.
Prompt: industrial brushed titanium machinery, gold structural rails, cobalt LEDs, bolts/grilles/copper piping, realistic non-toy physical detailing; three miners, two generators, one mining room.
