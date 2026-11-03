pluginManagement {
    val props=java.util.Properties()
    file("local.properties").inputStream().use { props.load(it) }
    includeBuild("${props.getProperty("flutter.sdk")}/packages/flutter_tools/gradle")
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "8.11.1" apply false
    id("org.jetbrains.kotlin.android") version "2.2.20" apply false
}
include(":app")
