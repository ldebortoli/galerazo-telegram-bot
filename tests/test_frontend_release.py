from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.frontend_release import FrontendRelease, PATHS, FEATURES, compatible, version

COMMIT = "b" * 40
SOURCE = "100644 blob " + "a" * 40 + " public/miniapp-assets/app.js"
FINGERPRINT = hashlib.sha256((SOURCE + "\n").encode()).hexdigest()
CONTRACT = {"schema": 1, "minimum_bot_version": "0.63", "features": sorted(FEATURES)}
METADATA = {**CONTRACT, "version": "0.1.14", "commit": COMMIT, "fingerprint": FINGERPRINT}
IMAGE = "us-central1-docker.pkg.dev/demo/bots/galerazobot:" + "c" * 12


class Fixture:
    def __init__(self, root, *, changed=True, dirty=False, fail_build=False, bad_asset=False, unhealthy=False):
        self.calls, self.changed = [], changed
        self.dirty, self.fail_build, self.bad_asset, self.unhealthy = dirty, fail_build, bad_asset, unhealthy
        self.deployed = not changed
        self.metadata = dict(METADATA)
        self.release = FrontendRelease(root, "demo", "us-central1-a", "galerazo-prod", run=self.run, get=self.get, sleep=lambda _: None)

    def run(self, args, *, cwd=None):
        self.calls.append(args)
        if args[0] == "gcloud":
            state = {"Running": not self.unhealthy, "Health": {"Status": "healthy"}}
            return json.dumps(state) + "\n" + IMAGE + "\n0.68"
        if args[0] == "git":
            op = args[1]
            if op == "remote": return "https://github.com/ldebortoli/galerazo-web.git"
            if op == "status": return " M app/a.ts" if self.dirty else ""
            if op == "symbolic-ref": return "main"
            if op == "rev-parse": return COMMIT
            if op == "ls-tree": return SOURCE
            if op == "worktree" and args[2] == "add":
                target = Path(args[4]); target.mkdir()
                (target / "release-contract.json").write_text(json.dumps(CONTRACT))
                (target / "package.json").write_text(json.dumps({"version": "0.1.14"}))
                assets = target / "public/miniapp-assets"; assets.mkdir(parents=True)
                for name in ("app.js", "core.js", "styles.css"): (assets / name).write_bytes(name.encode())
            return ""
        if args[-2:] == ["run", "build"] and self.fail_build: raise RuntimeError("build failed")
        if "deploy" in args and "--dry-run" not in args: self.deployed = True
        return ""

    def get(self, url):
        if url.endswith("release.json"):
            return (200, json.dumps(self.metadata).encode(), {}) if self.deployed else (404, b"", {})
        if url.endswith("/miniapp"):
            return 200, b"?v=0.1.14" if self.deployed else b"?v=0.1.10", {}
        if "/miniapp-assets/" in url:
            name = url.split("/miniapp-assets/")[1].split("?")[0]
            return 200, b"corrupt" if self.bad_asset else name.encode(), {}
        return 401, b'{"error":"telegram_required"}', {"Cache-Control": "no-store"}


class FrontendReleaseTests(unittest.TestCase):
    def test_contract_and_invalid_versions(self):
        self.assertIn("release-contract.json", PATHS)
        self.assertEqual(version("0.68"), (0, 68, 0))
        self.assertEqual(version("0.1.14"), (0, 1, 14))
        for bad in ("bad", "0", "1.2.3.4"):
            with self.assertRaises(ValueError): version(bad)
        compatible(METADATA, "0.68")
        for bad in ({**METADATA, "schema": 2}, {**METADATA, "commit": ""}, {**METADATA, "features": []}, {**METADATA, "minimum_bot_version": "0.69"}):
            with self.assertRaises(RuntimeError): compatible(bad, "0.68")
        with self.assertRaises(ValueError): FrontendRelease(".", "bad; shell", "zone", "instance")

    def test_pending_frontend_is_validated_published_and_verified(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root)
            result = f.release.sync("0.68")
            self.assertTrue(result["changed"])
            self.assertEqual(result["frontend_commit"], COMMIT)
            commands = f.calls
            self.assertTrue(any(args[-2:] == ["run", "coverage"] for args in commands))
            self.assertTrue(any("--dry-run" in args for args in commands))
            self.assertTrue(any("--tag" in args and COMMIT in args[-1] for args in commands))
            self.assertFalse(any("Publish-DockerImage" in str(args) or "Deploy-Gce" in str(args) for args in commands))
            self.assertIn("remove", commands[-1])

    def test_identical_or_documentation_only_source_does_not_build_or_publish(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root, changed=False)
            f.metadata["commit"] = "d" * 40
            result = f.release.sync("0.68")
            self.assertFalse(result["changed"])
            self.assertEqual(result["frontend_commit"], "d" * 40)
            self.assertFalse(any("npm-cli.js" in str(args) or "wrangler.js" in str(args) for args in f.calls))

    def test_dirty_frontend_and_unhealthy_backend_stop_before_any_upload(self):
        with tempfile.TemporaryDirectory() as root:
            for flags in ({"dirty": True}, {"unhealthy": True}):
                f = Fixture(root, **flags)
                with self.assertRaises(RuntimeError): f.release.sync("0.68")
                self.assertFalse(any("deploy" in args for args in f.calls))

    def test_build_failure_cleans_snapshot_and_never_uploads(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root, fail_build=True)
            with self.assertRaisesRegex(RuntimeError, "build failed"): f.release.sync("0.68")
            self.assertFalse(f.deployed)
            self.assertIn("remove", f.calls[-1])

    def test_served_asset_mismatch_or_wrong_bot_image_cannot_succeed(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root, changed=False, bad_asset=True)
            with self.assertRaisesRegex(RuntimeError, "asset mismatch"): f.release.sync("0.68")
            with self.assertRaisesRegex(RuntimeError, "active bot image"):
                f.release.verify({"metadata": METADATA, "assets": {}}, expected_image="wrong")
