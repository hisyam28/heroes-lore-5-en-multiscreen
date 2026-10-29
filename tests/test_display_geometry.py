"""Execute the runner's actual display/touch arithmetic as compiled ARM32 code."""
from pathlib import Path
import subprocess
import tempfile
import unittest

import test_arm32_relocations as arm

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(arm.unicorn and arm.COMPILERS, 'Requires the local NDK and Python unicorn')
class DisplayGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='geometry-', dir=ROOT / 'work')
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        source = directory / 'geometry.cpp'
        source.write_text('''#include "display_geometry.h"
#include "texture_layout.h"
extern "C" __attribute__((visibility("default")))
unsigned run_relocation(unsigned operation, int a, int b, int c) {
    if (operation == 6) return hl5::logical_height_for_surface(a,b);
    if (operation == 7 || operation == 8) {
        auto view=hl5::cover_display(a,b,hl5::logical_width_for_surface(a,b),hl5::logical_height_for_surface(a,b));
        if (operation==7) return unsigned(view.width)|(unsigned(view.height)<<16);
        return (unsigned(view.x)&65535)|((unsigned(view.y)&65535)<<16);
    }
    if (operation == 5) return hl5::texture_upload_bytes(a, b, unsigned(c) & 65535, unsigned(c) >> 16);
    if (operation == 0) return hl5::logical_width_for_surface(a, b);
    if (operation == 3) return hl5::map_display_coordinate(a, b, c, 492);
    if (operation == 4) return hl5::map_display_coordinate(a, b, c, 240);
    auto view = hl5::cover_display(a, b, c, 240);
    if (operation == 1) return (unsigned(view.x) & 65535) | ((unsigned(view.y) & 65535) << 16);
    return unsigned(view.width) | (unsigned(view.height) << 16);
}
''', encoding='utf-8')
        compiler = arm.COMPILERS[0]
        sysroot = compiler.parents[1] / 'sysroot'
        builtins = next((compiler.parents[1] / 'lib/clang').rglob('libclang_rt.builtins-arm-android.a'))
        library = directory / 'geometry.so'
        subprocess.run([str(compiler), '--target=armv7a-linux-androideabi26', '--sysroot=' + str(sysroot),
                        '-marm', '-shared', '-fPIC', '-std=c++17', '-O2', '-fno-exceptions', '-fno-rtti',
                        '-fno-stack-protector', '-fno-jump-tables', '-nostdlib', '-Wl,--no-undefined',
                        '-I' + str(ROOT / 'tools/runtime'), str(source), str(builtins), '-o', str(library)],
                       check=True, capture_output=True)
        cls.raw = library.read_bytes()
        cls.entry = arm.elf_symbols(cls.raw)['run_relocation'].address

    def execute(self, operation, a, b, c=0):
        return arm.Arm32Abs32Tests.run_policy(self, operation, a & 0xffffffff, b & 0xffffffff, c & 0xffffffff)

    def test_logical_width_matches_device_aspect_and_preserves_height(self):
        for width, height, logical in [(2620, 1280, 492), (2400, 1080, 534),
                                       (800, 480, 400), (1920, 1080, 428), (1080, 2400, 400)]:
            with self.subTest(surface=(width, height)):
                self.assertEqual(self.execute(0, width, height), logical)

    def test_uniform_viewport_covers_every_surface_edge(self):
        for width, height, logical in [(2620, 1280, 492), (800, 480, 492), (1080, 2400, 492)]:
            origin = self.execute(1, width, height, logical)
            extent = self.execute(2, width, height, logical)
            x, y = origin & 65535, origin >> 16
            if x >= 32768:
                x -= 65536
            if y >= 32768:
                y -= 65536
            w, h = extent & 65535, extent >> 16
            self.assertLessEqual(x, 0)
            self.assertLessEqual(y, 0)
            self.assertGreaterEqual(x + w, width)
            self.assertGreaterEqual(y + h, height)
            self.assertLessEqual(abs(w * 240 - h * logical), max(logical, 240))
            self.assertLessEqual(abs(2 * x + w - width), 1)
            self.assertLessEqual(abs(2 * y + h - height), 1)

    def test_touch_tracks_expanded_canvas_and_clamps_edges(self):
        self.assertEqual(self.execute(3, 0, 0, 2620), 0)
        self.assertEqual(self.execute(3, 1310, 0, 2620), 246)
        self.assertEqual(self.execute(3, 2619, 0, 2620), 491)
        self.assertEqual(self.execute(3, -30, 0, 2620), 0)
        self.assertEqual(self.execute(3, 3000, 0, 2620), 491)
        self.assertEqual(self.execute(4, 640, 1, 1278), 120)
        self.assertEqual(self.execute(4, 1280, 1, 1278), 239)

    def test_invalid_surface_and_touch_extents_are_safe(self):
        self.assertEqual(self.execute(0, 0, 1280), 400)
        self.assertEqual(self.execute(0, 2620, 0), 400)
        self.assertEqual(self.execute(2, 0, 1280, 492), 0)
        self.assertEqual(self.execute(3, 50, 0, 0), 0)

    def test_canvas_extends_height_on_narrow_and_square_screens(self):
        for width,height,logical_width,logical_height in [(2620,1280,492,240),
                (2340,1080,520,240),(1024,768,400,300),(1080,1080,400,400),(1080,2400,400,890)]:
            with self.subTest(surface=(width,height)):
                self.assertEqual(self.execute(0,width,height),logical_width)
                self.assertEqual(self.execute(6,width,height),logical_height)

    def test_adaptive_canvas_covers_common_phone_and_tablet_resolutions(self):
        for width,height in [(1280,720),(1920,1080),(2340,1080),(2620,1280),(2772,1280),
                (3200,1440),(3840,2160),(1024,768),(2048,1536),(1080,1080),(1080,2400)]:
            with self.subTest(surface=(width,height)):
                logical_w=self.execute(0,width,height);logical_h=self.execute(6,width,height)
                extent=self.execute(7,width,height);origin=self.execute(8,width,height)
                w,h=extent&65535,extent>>16
                x,y=origin&65535,origin>>16
                if x>=32768:x-=65536
                if y>=32768:y-=65536
                self.assertLessEqual(x,0);self.assertLessEqual(y,0)
                self.assertGreaterEqual(x+w,width);self.assertGreaterEqual(y+h,height)
                self.assertLessEqual(abs(w*logical_h-h*logical_w),max(logical_w,logical_h))

    def test_texture_copy_uses_actual_pixel_format_and_row_alignment(self):
        def texture(width, height, fmt, typ):
            return self.execute(5, width, height, fmt | (typ << 16))
        self.assertEqual(texture(492, 240, 0x1907, 0x8363), 492 * 240 * 2)
        self.assertEqual(texture(534, 240, 0x1907, 0x8363), 534 * 240 * 2)
        self.assertEqual(texture(5, 2, 0x1907, 0x1401), 16 + 15)
        self.assertEqual(texture(5, 2, 0x1908, 0x1401), 40)
        self.assertEqual(texture(5, 2, 0x1908, 0x8033), 12 + 10)
        self.assertEqual(texture(-1, 240, 0x1907, 0x8363), 0)
        self.assertEqual(texture(50000, 50000, 0x1908, 0x1401), 0)
        self.assertEqual(texture(492, 240, 0x1908, 0x8363), 0)


if __name__ == '__main__':
    unittest.main()
