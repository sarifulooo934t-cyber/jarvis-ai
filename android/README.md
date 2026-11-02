# JARVIS AI — Android app

Ye ek halka (light) WebView shell hai jo aapke deployed JARVIS server ko app ki tarah kholta hai.
Koi Play Store ki zaroorat nahi — APK phone me daal ke install kar lo.

## Pehle se bana hua APK
`jarvis-ai.apk` (is folder me) — seedha phone me copy karke install karo
(Settings → "Unknown sources" / "Install unknown apps" allow karna padega).

App kholne par pehli baar server ka URL maangega, jaise:
```
https://jarvis-ai.onrender.com
```
Phir app ke **Settings** tab me `JARVIS_TOKEN` daal ke Save karo — bas.

## Features
- Poora JARVIS web app (chat, browser control, YouTube, code, projects)
- Mic permission already wired — "Mic" button dabao aur bolo
- Long-press anywhere → Reload / server URL badlo / data clear
- Server down ho to friendly offline screen + retry

## Khud build karna
**Android Studio se:** is folder ko Android Studio me open karo → Run ▶.
(APK: Build → Build Bundle(s)/APK(s) → Build APK(s))

**Bina Android Studio (sirf command line):**
```bash
export JAVA_HOME=/path/to/jdk
export ANDROID_SDK=/path/to/android-sdk     # build-tools 34 + platforms/android-34
export ECJ_JAR=/path/to/ecj.jar             # https://repo1.maven.org/maven2/org/eclipse/jdt/ecj/3.33.0/ecj-3.33.0.jar
./build_apk.sh                              # -> jarvis-ai.apk
```

Default server URL badalna ho to `MainActivity.java` me `DEFAULT_URL` edit karo.
