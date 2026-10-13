package com.example.frontend

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.content.pm.PackageManager

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "civic/maps")
            .setMethodCallHandler { call, result ->
                if (call.method == "isMapsApiKeyConfigured") {
                    val metadata = packageManager.getApplicationInfo(
                        packageName,
                        PackageManager.GET_META_DATA,
                    ).metaData
                    result.success(
                        !metadata?.getString("com.google.android.geo.API_KEY").isNullOrBlank(),
                    )
                } else {
                    result.notImplemented()
                }
            }
    }
}
