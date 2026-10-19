# sbuild / Forge — APK build scaffold (V1.2)

Real Android APK requires Android SDK + Kotlin/Java toolchain.

## What this scaffold provides

1. `template/` — Android project skeleton that will host SBridge
2. `sbuild.json` — build config schema
3. Instructions to produce a debug APK when SDK is installed

## Config (sbuild.json)

```json
{
  "app_name": "SApp",
  "package": "com.s.lang.app",
  "entry": "main.s",
  "min_sdk": 24,
  "target_sdk": 34
}
```

## Future pipeline

```
main.s → SC/Spark → Kotlin → Gradle → APK
         (SBridge embeds SVM or interpreter)
```

## Current status

- Scaffold only (no APK without local Android SDK)
- SDX stubs define the API surface apps will call
