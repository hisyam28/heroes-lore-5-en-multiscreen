package co.kr.eamobile.hl5.runner;

import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;

/** API9-only launcher. Modern classes stay in classes2.dex, outside Dalvik. */
public final class CompatibilityActivity extends Activity {
    public static String routeFor(int sdk, String abi) {
        return sdk >= 21 && ("arm64-v8a".equals(abi) || "armeabi-v7a".equals(abi))
            ? "co.kr.eamobile.hl5.runner.MainActivity"
            : "co.kr.eamobile.HeroesLore5.HeroesLore5";
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        Intent launch = new Intent();
        launch.setClassName(this, routeFor(Build.VERSION.SDK_INT, Build.CPU_ABI));
        if (getIntent() != null) launch.putExtra("debug", getIntent().getBooleanExtra("debug", false));
        startActivity(launch);
        finish();
    }
}
