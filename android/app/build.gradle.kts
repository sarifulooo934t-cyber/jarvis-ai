plugins { id("com.android.application") }

android {
    namespace = "ai.jarvis.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "ai.jarvis.app"
        minSdk = 23
        targetSdk = 34
        versionCode = 2
        versionName = "2.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Signed APK banane ke liye apni keystore banao (README dekho)
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}
