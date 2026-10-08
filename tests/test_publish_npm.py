import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.publish_npm import release


class NpmPackagingTests(unittest.TestCase):
    def test_pack_from_directory_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="devin npm test ") as tmp:
            out = Path(tmp)
            pkg_dir = out / "launcher package"
            pkg_dir.mkdir()
            package = {"name": "devin-pack-test", "version": "1.0.0", "private": True}
            (pkg_dir / "package.json").write_text(json.dumps(package), encoding="utf-8")

            release(pkg_dir, "latest", "https://registry.npmjs.org/", publish=False, provenance=False)

            archive = out / "devin-pack-test-1.0.0.tgz"
            self.assertTrue(archive.is_file())
            with tarfile.open(archive) as tf:
                with tf.extractfile("package/package.json") as metadata:
                    self.assertEqual(json.load(metadata), package)


if __name__ == "__main__":
    unittest.main()
