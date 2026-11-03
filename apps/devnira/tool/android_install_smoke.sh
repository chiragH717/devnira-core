#!/usr/bin/env bash
set -euo pipefail
mkdir -p install-evidence
api=$(adb shell getprop ro.build.version.sdk | tr -d '\r')
echo "Android API $api" | tee install-evidence/RESULTS.txt
for role in User Admin; do
  if [[ "$role" == User ]]; then package=com.devnira.app; else package=com.devnira.admin; fi
  apk="install-apks/Devnira-$role-Demo/Devnira-$role-Demo.apk"
  test -f "$apk"
  # Record whether the original reported APK also fails on this Android image.
  baseline="baseline-apks/Devnira-$role-Demo/Devnira-$role-Demo.apk"
  if [[ -f "$baseline" ]]; then
    adb install --no-streaming "$baseline" > "install-evidence/$role-baseline.txt" 2>&1 || true
    adb uninstall "$package" >/dev/null 2>&1 || true
  fi
  adb logcat -c
  adb install --no-streaming "$apk" | tee "install-evidence/$role-install.txt"
  grep -q Success "install-evidence/$role-install.txt"
  adb shell am start -W -n "$package/com.devnira.app.MainActivity" | tee "install-evidence/$role-launch.txt"
  grep -q 'Status: ok' "install-evidence/$role-launch.txt"
  sleep 10
  pid=$(adb shell pidof "$package" | tr -d '\r')
  test -n "$pid"
  adb shell dumpsys activity activities > "install-evidence/$role-activities.txt"
  grep -E 'mResumedActivity|topResumedActivity' "install-evidence/$role-activities.txt" | grep -q "$package"
  adb logcat -d --pid="$pid" > "install-evidence/$role-logcat.txt"
  if grep -E 'FATAL EXCEPTION|Fatal signal|E/flutter.*Unhandled Exception' "install-evidence/$role-logcat.txt"; then
    echo "$role crashed"; exit 1
  fi
  adb exec-out screencap -p > "install-evidence/$role-api-$api.png"
  echo "$role: INSTALL + LAUNCH + RUNNING PASS (API $api)" | tee -a install-evidence/RESULTS.txt
  adb shell am force-stop "$package"
done
