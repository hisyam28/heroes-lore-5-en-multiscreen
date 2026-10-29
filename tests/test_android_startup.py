"""JVM regression model for the staged Activity's actual system-UI method.

Android Window/View are test doubles. This does not replace an Android device test.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / 'work/runner-target/app/src/main/java/co/kr/eamobile/hl5/runner/MainActivity.java'
JDKS = sorted((ROOT / 'work/android-tools').glob('jdk-*/bin/javac.exe'))


def extract_method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


@unittest.skipUnless(ACTIVITY.exists() and JDKS, 'Prepare the local runner and JDK for JVM regression tests')
class AndroidStartupModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='startup-model-', dir=ROOT / 'work')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory = Path(cls.temporary.name)
        cls.java = JDKS[0].with_name('java.exe')
        source = ACTIVITY.read_text(encoding='utf-8')
        method = extract_method(source, 'private void hideSystemUI()')
        frame_method = extract_method(source, 'public void onDrawFrame(').replace('GL10 gl', 'Object gl')
        status_method = extract_method(source, 'public void onNativeStatus(')
        exit_method = extract_method(source, 'public void onGameExitRequested(')
        fullscreen_method = extract_method(source, 'private void configureFullscreenWindow(')
        insets_method = extract_method(source, 'private void applyFullscreenInsets(')
        files = {
            'android/os/Build.java': '''package android.os;
public class Build { public static class VERSION { public static int SDK_INT = 36; } }
''',
            'android/view/WindowInsets.java': '''package android.view;
public class WindowInsets { public static class Type { public static int systemBars() { return 3; } } }
''',
            'android/view/WindowInsetsController.java': '''package android.view;
public class WindowInsetsController {
    public static final int BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE = 2;
    public int hides, behavior;
    public void hide(int types) { if (types != 3) throw new AssertionError(); hides++; }
    public void setSystemBarsBehavior(int value) { behavior = value; }
}
''',
            'android/view/View.java': '''package android.view;
public class View {
    public static final int SYSTEM_UI_FLAG_LAYOUT_STABLE=1, SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION=2,
        SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN=4, SYSTEM_UI_FLAG_HIDE_NAVIGATION=8,
        SYSTEM_UI_FLAG_FULLSCREEN=16, SYSTEM_UI_FLAG_IMMERSIVE_STICKY=32;
    public boolean attached;
    public int legacyCalls;
    public WindowInsetsController controller;
    public int visibility;
    public int[] padding = {19, 19, 19, 19};
    public void setPadding(int a, int b, int c, int d) { padding = new int[] {a,b,c,d}; }
    public void setVisibility(int value) { visibility = value; }
    public static final int VISIBLE=0, GONE=8;
    public boolean isAttachedToWindow() { return attached; }
    public WindowInsetsController getWindowInsetsController() {
        if (!attached) throw new AssertionError("Insets accessed before view attachment");
        return controller;
    }
    public void setSystemUiVisibility(int flags) { legacyCalls++; }
}
''',
            'android/view/Window.java': '''package android.view;
public class Window {
    public View decor;
    public boolean decorFits = true, contrast = true;
    public int flags;
    public WindowManager.LayoutParams attributes = new WindowManager.LayoutParams();
    public void addFlags(int value) { flags |= value; }
    public void setStatusBarColor(int value) {}
    public void setNavigationBarColor(int value) {}
    public WindowManager.LayoutParams getAttributes() { return attributes; }
    public void setAttributes(WindowManager.LayoutParams value) { attributes = value; }
    public void setNavigationBarContrastEnforced(boolean value) { contrast = value; }
    public void setDecorFitsSystemWindows(boolean value) { decorFits = value; }
    public View peekDecorView() { return decor; }
    public View getDecorView() {
        if (decor == null) decor = new View();
        return decor;
    }
    public WindowInsetsController getInsetsController() {
        // Reproduces the reported PhoneWindow dereference when decor is null.
        return decor.getWindowInsetsController();
    }
}
''',
            'android/view/WindowManager.java': '''package android.view;
public class WindowManager { public static class LayoutParams {
    public static final int FLAG_FULLSCREEN=1024, LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS=3,
        LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES=1;
    public int layoutInDisplayCutoutMode=0;
} }
''',
            'android/graphics/Color.java': '''package android.graphics;
public class Color { public static final int BLACK=0xff000000; }
''',
            'android/widget/TextView.java': '''package android.widget;
public class TextView extends android.view.View {
    public String text = "";
    public void setText(String value) { text = value; }
}
''',
            'android/util/Log.java': '''package android.util;
public class Log { public static int i(String tag, String value) { return 0; } }
''',
            'StartupHarness.java': '''import android.util.Log;
import android.graphics.Color;
public class StartupHarness {
    private android.view.Window window;
    private android.view.Window getWindow() { return window; }
    private static final String TAG="test";
    private int frameCount=0;
    private String latestStatus="";
    private boolean debugEnabled=false, exitRequested=false;
    private int finishCount=0;
    private void finishAndRemoveTask() { finishCount++; }
    private android.widget.TextView overlayTextView = new android.widget.TextView();
    private void runOnUiThread(Runnable action) { action.run(); }
    private String nativeStatus="FAIL BOOT: target kernel";
    private String nativeOnDrawFrame(boolean wantStatus) { return nativeStatus; }
    METHOD
    FRAME_METHOD
    STATUS_METHOD
    EXIT_METHOD
    FULLSCREEN_METHOD
    INSETS_METHOD
    public static void main(String[] args) {
        StartupHarness activity = new StartupHarness();
        if (args[0].startsWith("fullscreen_")) {
            int api=Integer.parseInt(args[0].substring(11));
            android.os.Build.VERSION.SDK_INT=api;
            activity.window=new android.view.Window();
            activity.configureFullscreenWindow();
            int expectedCutout=api >= 30 ? 3 : (api >= 28 ? 1 : 0);
            if (activity.window.attributes.layoutInDisplayCutoutMode != expectedCutout
                || (activity.window.flags & 1024) == 0
                || activity.window.decorFits != (api < 30)
                || activity.window.contrast != (api < 29)) throw new AssertionError("Fullscreen window policy");
            android.view.View view=new android.view.View();
            activity.applyFullscreenInsets(view);
            for (int value : view.padding) if (value != 0) throw new AssertionError("Insets shrink the game");
            return;
        }
        if (args[0].equals("no_status")) {
            activity.nativeStatus=null;
            activity.onDrawFrame(null);
            if (!activity.latestStatus.equals("")) throw new AssertionError("Null frame status published");
            return;
        }
        if (args[0].equals("normal_status") || args[0].equals("debug_status")) {
            activity.debugEnabled=args[0].equals("debug_status");
            activity.onNativeStatus("Original target engine running");
            int expected=activity.debugEnabled ? android.view.View.VISIBLE : android.view.View.GONE;
            if (activity.overlayTextView.visibility != expected) throw new AssertionError("Diagnostic visibility");
            return;
        }
        if (args[0].equals("exit_game")) {
            activity.onGameExitRequested();
            activity.onGameExitRequested();
            if (activity.finishCount != 1) throw new AssertionError("Exit must finish task once");
            return;
        }
        if (args[0].equals("persistent_error")) {
            for (int count : new int[] {179, 239}) {
                activity.frameCount=count;
                activity.onDrawFrame(null);
                if (activity.overlayTextView.visibility != android.view.View.VISIBLE
                    || !activity.overlayTextView.text.equals("FAIL BOOT: target kernel")
                    || !activity.latestStatus.equals(activity.overlayTextView.text))
                    throw new AssertionError("Boot error hidden or lost after frame " + (count+1));
            }
            return;
        }
        if (args[0].equals("null_window")) { activity.hideSystemUI(); return; }
        activity.window = new android.view.Window();
        if (args[0].equals("early_launch")) {
            activity.hideSystemUI();
            if (activity.window.decor != null) throw new AssertionError("Created decor prematurely");
            return;
        }
        android.view.View decor = new android.view.View();
        activity.window.decor = decor;
        if (args[0].equals("unattached")) { activity.hideSystemUI(); return; }
        decor.attached = true;
        if (args[0].equals("missing_controller")) { activity.hideSystemUI(); return; }
        decor.controller = new android.view.WindowInsetsController();
        if (args[0].equals("legacy")) android.os.Build.VERSION.SDK_INT = 26;
        activity.hideSystemUI();
        if (args[0].equals("legacy")) {
            if (decor.legacyCalls != 1 || decor.controller.hides != 0) throw new AssertionError("Legacy API path");
        } else {
            if (decor.controller.hides != 1 || decor.controller.behavior != 2 || decor.legacyCalls != 0)
                throw new AssertionError("Modern API path");
        }
    }
}
'''.replace('FRAME_METHOD', frame_method).replace('STATUS_METHOD', status_method).replace('EXIT_METHOD', exit_method).replace('FULLSCREEN_METHOD', fullscreen_method).replace('INSETS_METHOD', insets_method).replace('    METHOD', '    ' + method),
        }
        for relative, text in files.items():
            destination = cls.directory / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding='utf-8')
        subprocess.run([str(JDKS[0]), '-encoding', 'UTF-8', '-d', str(cls.directory),
                        *map(str, cls.directory.rglob('*.java'))], check=True, capture_output=True)

    def run_scenario(self, name):
        result = subprocess.run([str(self.java), '-cp', str(self.directory), 'StartupHarness', name],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_activity_before_decor_exists(self):
        self.run_scenario('early_launch')

    def test_null_window_and_unattached_view(self):
        for name in ('null_window', 'unattached'):
            with self.subTest(name=name):
                self.run_scenario(name)

    def test_attached_view_without_controller(self):
        self.run_scenario('missing_controller')

    def test_android_16_uses_attached_view_controller(self):
        self.run_scenario('modern')

    def test_android_8_keeps_legacy_system_ui_path(self):
        self.run_scenario('legacy')

    def test_boot_error_stays_visible_after_180_and_240_callbacks(self):
        self.run_scenario('persistent_error')

    def test_normal_launch_hides_status_and_debug_launch_shows_it(self):
        self.run_scenario('normal_status')
        self.run_scenario('debug_status')

    def test_game_exit_finishes_task_once(self):
        self.run_scenario('exit_game')

    def test_fullscreen_window_and_zero_insets_on_supported_android_versions(self):
        for api in (26, 28, 29, 30, 36):
            with self.subTest(api=api):
                self.run_scenario('fullscreen_' + str(api))

    def test_normal_render_accepts_no_diagnostic_string(self):
        self.run_scenario('no_status')


if __name__ == '__main__':
    unittest.main()
