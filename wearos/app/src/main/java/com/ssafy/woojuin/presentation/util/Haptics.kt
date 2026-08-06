package com.ssafy.woojuin.presentation.util

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext

/**
 * 공통 햅틱 피드백.
 * - 기능 시작: 가벼운 클릭
 * - 녹음 종료: 짧은 종료 피드백
 * - 저장 성공: 성공 햅틱
 * - 오류: 이중 짧은 햅틱
 */
class Haptics(private val vibrator: Vibrator?) {

    fun tapStart() = play(VibrationEffect.createPredefined(VibrationEffect.EFFECT_CLICK))

    fun stopCapture() = play(VibrationEffect.createPredefined(VibrationEffect.EFFECT_TICK))

    fun success() = play(
        VibrationEffect.createWaveform(longArrayOf(0, 40, 60, 60), intArrayOf(0, 120, 0, 200), -1)
    )

    fun error() = play(VibrationEffect.createPredefined(VibrationEffect.EFFECT_DOUBLE_CLICK))

    private fun play(effect: VibrationEffect) {
        vibrator?.takeIf { it.hasVibrator() }?.vibrate(effect)
    }

    companion object {
        /**
         * VibratorManager 는 API 31 부터다. minSdk 가 30 이라 분기가 **필요하다** —
         * Wear OS 3.x 가 곧 API 30 이고 갤럭시 워치 4·5 가 거기 머물러 있을 수 있다.
         * 분기 없이 부르면 그 기기에서 진동이 통째로 죽는다(서비스 조회가 null).
         */
        fun from(context: Context): Haptics {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val manager =
                    context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
                manager?.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
            }
            return Haptics(vibrator)
        }
    }
}

@Composable
fun rememberHaptics(): Haptics {
    val context = LocalContext.current
    return remember { Haptics.from(context) }
}
