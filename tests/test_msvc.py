"""Offline wrapper checks and optional local-toolchain smoke test."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import msvc


class MsvcTest(unittest.TestCase):
    def test_paths(self):
        for original, expected in {
            "/showIncludes": "/showIncludes",
            "/nologo": "/nologo",
            "/DROOT=a/b": "/DROOT=a/b",
            "/Fo/tmp/a b.obj": r"/FoZ:\tmp\a b.obj",
            "/I/tmp/header files": r"/IZ:\tmp\header files",
            "/OUT:/tmp/a.exe": r"/OUT:Z:\tmp\a.exe",
            "/LIBPATH:C:\\SDK": r"/LIBPATH:C:\SDK",
            "/tmp/app.c": r"Z:\tmp\app.c",
            "/Foout/hello.obj": "/Fo" + msvc.wine_path("out/hello.obj"),
            "src/app.c": msvc.wine_path("src/app.c"),
            "@args.rsp": "@" + msvc.wine_path("args.rsp"),
        }.items():
            with self.subTest(original=original):
                self.assertEqual(msvc.translate(original), expected)

    def test_environment(self):
        inherited = {"PATH": "/usr/bin", "INCLUDE": r"C:\custom",
                     "WINEPREFIX": "/game", "WINEARCH": "win64"}
        env = msvc.compiler_env(Path("/opt/vc test"), inherited)
        self.assertEqual(env["PATH"], inherited["PATH"])
        self.assertEqual(env["WINEPREFIX"], str(msvc.PREFIX))
        self.assertNotIn("WINEARCH", env)
        self.assertEqual(env["WINEDEBUG"], "-all")
        self.assertIn(r"Z:\opt\vc test\Vc7\bin", env["WINEPATH"].split(";"))
        self.assertIn(r"Z:\opt\vc test\Vc7\PlatformSDK\lib", env["LIB"].split(";"))
        self.assertEqual(env["INCLUDE"].split(";")[-1], inherited["INCLUDE"])

    def test_shim_quotes_and_propagates(self):
        with tempfile.TemporaryDirectory(prefix="shim's space ") as temp:
            script = Path(temp) / "wrapper.py"
            script.write_text(
                "import sys\nprint(repr(sys.argv[1:]))\nsys.exit(17)\n"
            )
            shim = Path(temp) / "cl"
            shim.write_text(msvc.shim_text(script, "cl"))
            shim.chmod(0o755)
            result = subprocess.run([shim, "arg with spaces", "$test"], capture_output=True,
                                    text=True)
            self.assertEqual(result.returncode, 17)
            self.assertEqual(result.stdout.strip(), "['cl', 'arg with spaces', '$test']")

    def test_manifest(self):
        contents = (msvc.ROOT / "re/toolchain.sha256").read_text()
        self.assertEqual(set(msvc.parse_hashes(contents)), msvc.FILES)
        lines = contents.splitlines()
        for invalid in ("\n".join(lines[1:]), contents + lines[0], "bad  Vc7/bin/cl.exe"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                msvc.parse_hashes(invalid)

    @unittest.skipUnless(os.environ.get("ROTK_MSVC_IT") == "1", "requires local MSVC and Wine")
    def test_hello(self):
        subprocess.run(["make", "hello"], cwd=msvc.ROOT, check=True)
