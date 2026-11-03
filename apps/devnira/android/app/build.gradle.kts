plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("dev.flutter.flutter-gradle-plugin")
}
android {
    namespace = "com.devnira.app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    defaultConfig {
        applicationId = "com.devnira.app"
        minSdk = 24
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }
    flavorDimensions += "role"
    productFlavors {
        create("player") {
            dimension = "role"
            applicationId = "com.devnira.app"
            manifestPlaceholders["appLabel"] = "Devnira Demo"
        }
        create("admin") {
            dimension = "role"
            applicationId = "com.devnira.admin"
            manifestPlaceholders["appLabel"] = "Devnira Admin Demo"
        }
    }
    signingConfigs {
        getByName("debug") {
            enableV1Signing = true
            enableV2Signing = true
            enableV3Signing = true
        }
    }
    // Extract compressed native libraries instead of relying on direct APK mmap.
    // This also accommodates vendor package installers with stricter ZIP handling.
    packaging {
        jniLibs { useLegacyPackaging = true }
    }
    buildTypes {
        release { signingConfig = signingConfigs.getByName("debug") }
    }
}
flutter { source = "../.." }
