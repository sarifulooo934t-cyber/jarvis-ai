#!/usr/bin/env bash
# Builds app-release-unsigned -> signed APK without Gradle (aapt2 + ecj + d8 + apksigner).
# Needs: JAVA_HOME pointing at a JDK/JRE (java, keytool), Android build-tools + platform android.jar,
#        ecj.jar (Eclipse compiler, works on a plain JRE).
#
# Usage:
#   ANDROID_SDK=/path/to/sdk ECJ_JAR=/path/to/ecj.jar ./build_apk.sh
# Output: build/jarvis-ai.apk
set -euo pipefail
# small containers often cap virtual address space; the JVM needs much more
ulimit -v unlimited 2>/dev/null || true

HERE="$(cd "$(dirname "$0")" && pwd)"
SDK="${ANDROID_SDK:?set ANDROID_SDK}"
ECJ="${ECJ_JAR:?set ECJ_JAR (ecj.jar)}"
BT="$(ls -d "$SDK"/android-* | grep -v 'android-3[0-9]$' | head -1)"
PLATFORM_JAR="$SDK/android-34/android.jar"
JAVA="${JAVA:-java}"
JAVA_OPTS="${JAVA_OPTS:--Xmx512m}"
export JAVA_OPTS

BUILD="$HERE/build"
SRC="$HERE/app/src/main"
rm -rf "$BUILD"
mkdir -p "$BUILD/gen" "$BUILD/classes" "$BUILD/dex"

echo "==> 1/6 aapt2 compile resources"
"$BT/aapt2" compile --dir "$SRC/res" -o "$BUILD/res.zip"

echo "==> 2/6 aapt2 link"
"$BT/aapt2" link \
  -o "$BUILD/base.apk" \
  -I "$PLATFORM_JAR" \
  --manifest "$SRC/AndroidManifest.xml" \
  --java "$BUILD/gen" \
  --min-sdk-version 23 --target-sdk-version 34 \
  --auto-add-overlay \
  "$BUILD/res.zip"

echo "==> 3/6 compile java"
find "$BUILD/gen" "$SRC/java" -name '*.java' > "$BUILD/sources.txt"
"$JAVA" $JAVA_OPTS -jar "$ECJ" \
  -source 8 -target 8 \
  -bootclasspath "$PLATFORM_JAR" -classpath "$PLATFORM_JAR" \
  -proc:none -nowarn -d "$BUILD/classes" @"$BUILD/sources.txt"

echo "==> 4/6 dex (d8)"
find "$BUILD/classes" -name '*.class' > "$BUILD/classes.txt"
"$BT/d8" -JXmx512m --lib "$PLATFORM_JAR" --min-api 23 --output "$BUILD/dex" @"$BUILD/classes.txt"

echo "==> 5/6 add dex + zipalign"
cp "$BUILD/dex/classes.dex" "$BUILD/"
python3 - "$BUILD/base.apk" "$BUILD/classes.dex" <<'PY'
import sys, zipfile
apk, dex = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(apk, "a", zipfile.ZIP_DEFLATED) as z:
    z.write(dex, "classes.dex")
PY
"$BT/zipalign" -f -p 4 "$BUILD/base.apk" "$BUILD/aligned.apk"

echo "==> 6/6 sign"
KS="$BUILD/jarvis-debug.keystore"
if [ ! -f "$KS" ]; then
  keytool -genkeypair -v -keystore "$KS" -storepass android -keypass android \
    -alias jarvis -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=JARVIS AI, OU=Personal, O=JARVIS, L=India, C=IN" >/dev/null 2>&1
fi
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
  --min-sdk-version 23 --out "$HERE/jarvis-ai.apk" "$BUILD/aligned.apk"

"$BT/apksigner" verify --print-certs "$HERE/jarvis-ai.apk" | head -4
ls -lh "$HERE/jarvis-ai.apk"
echo "Done: $HERE/jarvis-ai.apk"
