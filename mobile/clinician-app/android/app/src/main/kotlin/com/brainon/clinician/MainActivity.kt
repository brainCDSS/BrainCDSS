package com.brainon.clinician

import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "brainon_high_importance",
                "BrainOn alerts",
                NotificationManager.IMPORTANCE_HIGH,
            )
            channel.description = "Clinical and account notifications"
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }
}
