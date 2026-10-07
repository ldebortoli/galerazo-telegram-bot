from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError

import pytest

from scripts import frontend_release as bridge
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
    def setUp(self):
        toolchain = tempfile.TemporaryDirectory()
        self.addCleanup(toolchain.cleanup)
        node = Path(toolchain.name) / "node"
        npm = node.parent / "node_modules/npm/bin/npm-cli.js"
        npm.parent.mkdir(parents=True)
        npm.write_text("// Fixture; subprocesses are simulated by Fixture.run.\n", encoding="utf-8")
        lookup = patch("scripts.frontend_release.shutil.which", return_value=str(node))
        lookup.start()
        self.addCleanup(lookup.stop)

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

    def test_missing_node_or_npm_cleans_snapshot_before_any_upload(self):
        with tempfile.TemporaryDirectory() as root:
            for node, error in ((None, "Node.js is required"), (str(Path(root) / "missing-node"), "npm CLI is unavailable")):
                with self.subTest(error=error), patch("scripts.frontend_release.shutil.which", return_value=node):
                    f = Fixture(root)
                    with self.assertRaisesRegex(RuntimeError, error):
                        f.release.sync("0.68")
                    self.assertFalse(f.deployed)
                    self.assertFalse(any("deploy" in args for args in f.calls))
                    self.assertIn("remove", f.calls[-1])

    def test_served_asset_mismatch_or_wrong_bot_image_cannot_succeed(self):
        with tempfile.TemporaryDirectory() as root:
            f = Fixture(root, changed=False, bad_asset=True)
            with self.assertRaisesRegex(RuntimeError, "asset mismatch"): f.release.sync("0.68")
            with self.assertRaisesRegex(RuntimeError, "active bot image"):
                f.release.verify({"metadata": METADATA, "assets": {}}, expected_image="wrong")


@pytest.mark.parametrize("windows", [False, True])
def test_subprocess_boundary_keeps_credentials_out_of_errors_and_disables_telemetry(tmp_path, windows):
    gcloud = tmp_path / "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
    gcloud.parent.mkdir(parents=True)
    gcloud.write_text("fixture", encoding="utf-8")
    environment = {"LOCALAPPDATA": str(tmp_path), "EXISTING_SETTING": "preserved"}
    process = Mock(return_value=SimpleNamespace(returncode=0, stdout=" response \n"))
    with patch.object(bridge, "os", SimpleNamespace(name="nt" if windows else "posix", environ=environment)), patch.object(bridge.subprocess, "run", process):
        assert bridge.command(["gcloud", "--command", "one\ntwo\n"], cwd=tmp_path) == "response"
        args, options = process.call_args
        assert args[0][0] == (str(gcloud) if windows else "gcloud")
        assert args[0][-1] == ("one; two" if windows else "one\ntwo\n")
        assert options["cwd"] == tmp_path and options["timeout"] == 1800
        assert options["env"] == {**environment, "CI": "true", "WRANGLER_WRITE_LOGS": "false", "WRANGLER_SEND_METRICS": "false"}
        process.return_value = SimpleNamespace(returncode=23, stdout="credential-sentinel", stderr="credential-sentinel")
        with pytest.raises(RuntimeError) as error:
            bridge.command(["gcloud", "--command", "safe"])
        assert "exit 23" in str(error.value) and "credential-sentinel" not in str(error.value)


def test_missing_windows_gcloud_stops_before_subprocess(tmp_path):
    with patch.object(bridge, "os", SimpleNamespace(name="nt", environ={"LOCALAPPDATA": str(tmp_path)})), patch.object(bridge.subprocess, "run") as process:
        with pytest.raises(RuntimeError, match="Google Cloud CLI is unavailable"):
            bridge.command(["gcloud", "--command", "safe"])
        process.assert_not_called()


def test_http_adapter_preserves_status_headers_and_bounds_reads():
    response = MagicMock()
    response.__enter__.return_value = response
    response.status, response.headers = 200, {"Cache-Control": "no-store"}
    response.read.return_value = b"{}"
    with patch.object(bridge, "urlopen", return_value=response) as open_url:
        assert bridge.http("https://fixture.invalid/miniapp/release.json") == (200, b"{}", {"Cache-Control": "no-store"})
        request = open_url.call_args.args[0]
        assert request.full_url == "https://fixture.invalid/miniapp/release.json"
        assert request.get_header("Cache-control") == "no-cache"
        assert open_url.call_args.kwargs["timeout"] == 20
        response.read.assert_called_once_with(65537)
    failure = HTTPError("https://fixture.invalid", 503, "unavailable", {"Retry-After": "5"}, io.BytesIO(b"try later"))
    with patch.object(bridge, "urlopen", side_effect=failure):
        assert bridge.http("https://fixture.invalid") == (503, b"try later", {"Retry-After": "5"})


@pytest.mark.parametrize("responses,legacy,error", [
    ([(503, b"unavailable", {})], False, RuntimeError),
    ([(200, b"x" * 65537, {})], False, RuntimeError),
    ([(200, b"not json", {})], False, ValueError),
    ([(404, b"", {})], False, RuntimeError),
    ([(404, b"", {}), (503, b"?v=0.1.10", {})], True, RuntimeError),
    ([(404, b"", {}), (200, b"?v=0.1.13", {})], True, ValueError),
])
def test_unavailable_or_unrecognized_frontend_never_bootstraps_a_release(tmp_path, responses, legacy, error):
    get = Mock(side_effect=responses)
    release = FrontendRelease(tmp_path, "demo", "zone", "instance", get=get)
    with pytest.raises(error):
        release.metadata("https://fixture.invalid", legacy=legacy)
    assert get.call_count == len(responses)


def test_contract_rejects_bad_fingerprint_and_allows_pre_album_legacy_bot():
    with pytest.raises(RuntimeError, match="metadata"):
        compatible({**METADATA, "fingerprint": "broken"}, "0.68")
    compatible({**METADATA, "features": []}, "0.64")


@pytest.mark.parametrize("route,response,message", [
    ("release.json", (200, json.dumps({**METADATA, "commit": "d" * 40}).encode(), {}), "selected source"),
    ("/miniapp", (503, b"?v=0.1.14", {}), "document version"),
    ("/miniapp", (200, b"?v=0.1.13", {}), "document version"),
    ("app.js?v=0.1.14", (404, b"app.js", {}), "asset mismatch"),
    ("/bootstrap", (200, b'{"error":"telegram_required"}', {"Cache-Control": "no-store"}), "gateway"),
    ("/bootstrap", (401, b'{"error":"other"}', {"Cache-Control": "no-store"}), "gateway"),
    ("/bootstrap", (401, b'{"error":"telegram_required"}', {"Cache-Control": "public"}), "gateway"),
])
def test_release_verification_requires_source_document_assets_and_closed_gateway(tmp_path, route, response, message):
    fixture = Fixture(tmp_path, changed=False)
    fixture.release.get = lambda url: response if url.endswith(route) else fixture.get(url)
    plan = {"metadata": METADATA, "assets": {"app.js": hashlib.sha256(b"app.js").hexdigest()}}
    with pytest.raises(RuntimeError, match=message):
        fixture.release.verify(plan)
    assert all(call[0] == "gcloud" for call in fixture.calls)


def test_verification_checks_both_domains_and_accepts_lowercase_cache_header(tmp_path):
    fixture = Fixture(tmp_path, changed=False)
    requested = []
    def get(url):
        requested.append(url)
        if url.endswith("/bootstrap"):
            return 401, b'{"error":"telegram_required"}', {"cache-control": "no-store"}
        return fixture.get(url)
    fixture.release.get = get
    evidence = fixture.release.verify({"metadata": METADATA, "assets": {}}, expected_image=IMAGE)
    assert evidence == {"bot_version": "0.68", "bot_image": IMAGE, "frontend_commit": COMMIT, "frontend_version": "0.1.14"}
    assert {url.removesuffix("/miniapp/api/bootstrap") for url in requested if url.endswith("/bootstrap")} == set(bridge.DOMAINS)


@pytest.mark.parametrize("override,error", [
    ({"remote": "https://github.com/other/project"}, "Unexpected frontend repository"),
    ({"symbolic-ref": "feature"}, "must be on main"),
    ({"fetch": RuntimeError("fetch failed")}, "fetch failed"),
    ({"rev-parse-local": "c" * 40, "merge-base": RuntimeError("diverged")}, "diverged"),
])
def test_repository_identity_and_git_failures_block_before_snapshot_or_external_release(tmp_path, override, error):
    fixture = Fixture(tmp_path)
    original = fixture.run
    def run(args, *, cwd=None):
        if args[0] == "git":
            operation = "rev-parse-local" if args[1:] == ["rev-parse", "refs/heads/main"] else args[1]
            if operation in override:
                fixture.calls.append(args)
                value = override[operation]
                if isinstance(value, Exception):
                    raise value
                return value
        return original(args, cwd=cwd)
    fixture.release.run = run
    with pytest.raises(RuntimeError, match=error):
        fixture.release.sync("0.68")
    assert not any("worktree" in call or "deploy" in call or call[0] == "gcloud" for call in fixture.calls)


def test_remote_fast_forward_uses_remote_snapshot_without_mutating_live_checkout(tmp_path):
    fixture = Fixture(tmp_path, changed=False)
    original = fixture.run
    def run(args, *, cwd=None):
        if args == ["git", "rev-parse", "refs/heads/main"]:
            fixture.calls.append(args)
            return "c" * 40
        return original(args, cwd=cwd)
    fixture.release.run = run
    result = fixture.release.sync("0.68")
    assert result["changed"] is False
    assert ["git", "merge-base", "--is-ancestor", "c" * 40, COMMIT] in fixture.calls
    assert next(call for call in fixture.calls if call[1:3] == ["worktree", "add"])[-1] == COMMIT
    assert not any(call[1] in {"pull", "checkout", "reset", "merge"} for call in fixture.calls)


def test_missing_metadata_cannot_be_treated_as_an_unchanged_release(tmp_path):
    fixture = Fixture(tmp_path, changed=False)
    fixture.release.get = lambda _: (404, b"", {})
    with pytest.raises(RuntimeError, match="metadata unavailable"):
        fixture.release.sync("0.68")
    assert not any("worktree" in call or "deploy" in call for call in fixture.calls)


@pytest.mark.parametrize("failure", ["contract", "dirty_snapshot", "dry_run"])
def test_validation_failure_removes_snapshot_without_upload(tmp_path, failure):
    fixture = Fixture(tmp_path)
    node = tmp_path / "node"
    npm = tmp_path / "node_modules/npm/bin/npm-cli.js"
    npm.parent.mkdir(parents=True)
    npm.write_text("fixture", encoding="utf-8")
    original = fixture.run
    def run(args, *, cwd=None):
        result = original(args, cwd=cwd)
        if failure == "contract" and args[1:3] == ["worktree", "add"]:
            (Path(args[4]) / "release-contract.json").write_text("not json", encoding="utf-8")
        if failure == "dirty_snapshot" and args[1] == "status" and Path(cwd) != fixture.release.repository:
            return " M app/a.ts"
        if failure == "dry_run" and "--dry-run" in args:
            raise RuntimeError("dry run failed")
        return result
    fixture.release.run = run
    with patch.object(bridge.shutil, "which", return_value=str(node)), pytest.raises((RuntimeError, ValueError)):
        fixture.release.sync("0.68")
    assert not fixture.deployed
    assert not any("deploy" in call and "--dry-run" not in call for call in fixture.calls)
    assert fixture.calls[-1][1:3] == ["worktree", "remove"]


def test_propagation_retry_is_bounded_and_does_not_repeat_upload(tmp_path, capsys):
    fixture = Fixture(tmp_path)
    node = tmp_path / "node"
    npm = tmp_path / "node_modules/npm/bin/npm-cli.js"
    npm.parent.mkdir(parents=True)
    npm.write_text("fixture", encoding="utf-8")
    original = fixture.run
    def run(args, *, cwd=None):
        result = original(args, cwd=cwd)
        if "deploy" in args and "--dry-run" not in args:
            return "Current Version ID: 12345678-1234-1234-1234-123456789abc"
        return result
    fixture.release.run = run
    verify = fixture.release.verify
    attempts = []
    def eventual(plan):
        attempts.append(plan)
        if len(attempts) < 3:
            raise RuntimeError("propagating")
        return verify(plan)
    fixture.release.verify = eventual
    fixture.release.sleep = Mock()
    with patch.object(bridge.shutil, "which", return_value=str(node)):
        result = fixture.release.sync("0.68")
    assert result["frontend_commit"] == COMMIT
    assert len(attempts) == 3 and fixture.release.sleep.call_args_list == [unittest.mock.call(5)] * 2
    assert sum("deploy" in call and "--dry-run" not in call for call in fixture.calls) == 1
    assert "12345678-1234-1234-1234-123456789abc" in capsys.readouterr().out


def test_permanent_verification_failure_stops_after_six_attempts_and_cleans_snapshot(tmp_path):
    fixture = Fixture(tmp_path, changed=False)
    fixture.release.verify = Mock(side_effect=OSError("offline"))
    fixture.release.sleep = Mock()
    with pytest.raises(OSError, match="offline"):
        fixture.release.sync("0.68")
    assert fixture.release.verify.call_count == 6 and fixture.release.sleep.call_count == 5
    assert fixture.calls[-1][1:3] == ["worktree", "remove"]


@pytest.mark.parametrize("stage", ["sync", "verify"])
def test_cli_persists_sync_plan_and_passes_expected_image_to_verify(tmp_path, capsys, stage):
    plan_file = tmp_path / "results" / "frontend.json"
    evidence = {"bot_version": "0.68", "bot_image": IMAGE, "frontend_commit": COMMIT, "frontend_version": "0.1.14"}
    plan = {"metadata": METADATA, "assets": {"app.js": "hash"}, "changed": True, **evidence}
    release = Mock()
    release.sync.return_value = plan
    release.verify.return_value = evidence
    if stage == "verify":
        plan_file.parent.mkdir()
        plan_file.write_text(json.dumps(plan), encoding="utf-8")
    argv = ["frontend_release.py", "--stage", stage, "--repository", str(tmp_path), "--project", "demo", "--zone", "zone", "--instance", "instance", "--result", str(plan_file), "--target-bot-version", "0.68", "--expected-image", IMAGE]
    with patch.object(sys, "argv", argv), patch.object(bridge, "FrontendRelease", return_value=release) as create:
        bridge.main()
    create.assert_called_once_with(str(tmp_path), "demo", "zone", "instance")
    if stage == "sync":
        release.sync.assert_called_once_with("0.68")
        release.verify.assert_not_called()
    else:
        release.verify.assert_called_once_with(plan, expected_image=IMAGE)
        release.sync.assert_not_called()
    assert json.loads(plan_file.read_text(encoding="utf-8")) == plan
    assert json.loads(capsys.readouterr().out) == evidence


def test_cli_requires_target_version_before_sync(tmp_path, capsys):
    argv = ["frontend_release.py", "--stage", "sync", "--repository", str(tmp_path), "--project", "demo", "--zone", "zone", "--instance", "instance", "--result", str(tmp_path / "result.json")]
    with patch.object(sys, "argv", argv), patch.object(bridge, "FrontendRelease") as create, pytest.raises(SystemExit) as error:
        bridge.main()
    assert error.value.code == 2
    assert "sync requires --target-bot-version" in capsys.readouterr().err
    create.return_value.sync.assert_not_called()


def test_script_entrypoint_has_safe_help_without_touching_external_services(capsys):
    with patch.object(sys, "argv", ["frontend_release.py", "--help"]), patch.object(bridge.subprocess, "run") as run, patch("urllib.request.urlopen") as get, pytest.raises(SystemExit) as error:
        runpy.run_path(str(Path(bridge.__file__)), run_name="__main__")
    assert error.value.code == 0
    assert "--stage" in capsys.readouterr().out
    run.assert_not_called()
    get.assert_not_called()


@pytest.mark.skipif(os.name != "nt", reason="The release wrapper requires Windows PowerShell and the project .venv")
def test_powershell_release_wrapper_executes_selected_snapshot_with_existing_runtime(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    powershell = shutil.which("powershell")
    if not powershell or not (repository / ".venv/Scripts/python.exe").is_file():
        pytest.skip("Windows PowerShell or the existing project .venv is unavailable")
    snapshot = tmp_path / "selected source"
    (snapshot / "scripts").mkdir(parents=True)
    (snapshot / "galerazo_bot").mkdir()
    (snapshot / ".python-version").write_text(".".join(map(str, sys.version_info[:3])), encoding="utf-8")
    (snapshot / "galerazo_bot/versioning.py").write_text('CURRENT_VERSION = "9.8"\n', encoding="utf-8")
    selected_script = snapshot / "scripts/frontend_release.py"
    selected_script.write_text(
        "import json, pathlib, sys\n"
        "arguments = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
        "pathlib.Path(arguments['--result']).write_text(json.dumps({'source': __file__, 'arguments': arguments}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    result = tmp_path / "result.json"
    process = subprocess.run([
        powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(repository / "scripts/deploy/Invoke-FrontendRelease.ps1"),
        "-Stage", "verify", "-FrontendRepositoryPath", str(tmp_path / "frontend"), "-RuntimeRepositoryPath", str(repository),
        "-BotSourceRoot", str(snapshot), "-ResultFile", str(result), "-ProjectId", "demo", "-Zone", "zone", "-Instance", "instance", "-ExpectedImage", IMAGE,
    ], capture_output=True, text=True, timeout=30, check=False)
    assert process.returncode == 0, process.stderr
    recorded = json.loads(result.read_text(encoding="utf-8"))
    assert Path(recorded["source"]).resolve() == selected_script.resolve()
    assert recorded["arguments"]["--target-bot-version"] == "9.8"
    assert recorded["arguments"]["--expected-image"] == IMAGE
    assert recorded["arguments"]["--stage"] == "verify"
