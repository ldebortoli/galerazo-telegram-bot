from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts import registry_retention as retention


PREFIX = "us-central1-docker.pkg.dev/demo-project/bots/galerazobot"
A, B, C = ("sha256:" + character * 64 for character in "abc")


def manager():
    return retention.RegistryRetention("demo-project", "us-central1", "bots", "us-central1-a", "bot-vm")


def snapshot():
    return {"production": PREFIX + ":current", "rollback": PREFIX + ":previous",
            "containers": [{"id": "active", "image": PREFIX + ":previous",
                            "digests": [PREFIX + "@" + C], "started": "now"}]}


STATE = {"format": "DOCKER", "mode": "STANDARD_REPOSITORY"}


def prepare_sync(target):
    before = snapshot()
    target.snapshot = Mock(return_value=before)
    target.repository_state = Mock(return_value=deepcopy(STATE))
    target.digest = Mock(side_effect=lambda ref: {
        PREFIX + ":current": A, PREFIX + ":previous": B, PREFIX + "@" + C: C,
        PREFIX + ":candidate": "sha256:" + "d" * 64}[ref])
    target.set_policies = Mock()
    return before


@pytest.mark.parametrize("suffix", ["", "-sidecar", "/sidecar"])
def test_read_snapshot_protects_real_digests_and_stopped_containers(tmp_path, suffix):
    (tmp_path / "image.env").write_text("# comment\nGALERAZO_IMAGE=" + PREFIX + ":current\n")
    (tmp_path / "previous-image.env").write_text("GALERAZO_IMAGE=" + PREFIX + ":previous\n")
    unrelated = {"Config": {"Image": PREFIX.replace("/galerazobot", "/unrelated") + ":tag"}}
    managed = {"Id": "b", "Config": {"Image": PREFIX + suffix + ":old-tunnel"}, "Image": "local-image",
               "State": {"StartedAt": "yesterday", "Status": "exited"}}
    def docker(args, **kwargs):
        if args == ["docker", "ps", "-aq"]:
            return "other managed"
        if args[:2] == ["docker", "inspect"]:
            return json.dumps([unrelated if args[-1] == "other" else managed])
        assert args == ["docker", "image", "inspect", "local-image"]
        return json.dumps([{"RepoDigests": [PREFIX + suffix + "@" + C, "other/repo@" + A]}])
    with patch.object(retention, "Path", return_value=tmp_path), patch.object(
            retention.subprocess, "check_output", side_effect=docker):
        result = retention.read_snapshot(PREFIX)
    assert result["production"] == PREFIX + ":current"
    assert result["rollback"] == PREFIX + ":previous"
    assert result["containers"] == [{"id": "b", "image": PREFIX + suffix + ":old-tunnel",
                                      "digests": [PREFIX + suffix + "@" + C], "started": "yesterday"}]


@pytest.mark.parametrize("text", ["", "GALERAZO_IMAGE=foreign:tag", "GALERAZO_IMAGE=" + PREFIX + ":a\nGALERAZO_IMAGE=" + PREFIX + ":b"])
def test_read_snapshot_rejects_incomplete_or_foreign_files(tmp_path, text):
    (tmp_path / "image.env").write_text(text)
    with patch.object(retention, "Path", return_value=tmp_path), pytest.raises(RuntimeError):
        retention.read_snapshot(PREFIX)


def test_read_snapshot_initial_install_and_missing_actual_digest(tmp_path):
    with patch.object(retention, "Path", return_value=tmp_path), patch.object(
            retention.subprocess, "check_output", return_value=""):
        assert retention.read_snapshot(PREFIX) == {"production": None, "rollback": None, "containers": []}
    item = {"Id": "container", "Config": {"Image": PREFIX + "@" + A}, "Image": "local", "State": {"StartedAt": "now"}}
    for actual, message in (({}, "actual container"), ({"RepoDigests": [PREFIX + "@" + A]}, "without a production")):
        with patch.object(retention, "Path", return_value=tmp_path), patch.object(
                retention.subprocess, "check_output", side_effect=["container", json.dumps([item]), json.dumps([actual])]), pytest.raises(RuntimeError, match=message):
            retention.read_snapshot(PREFIX)


@pytest.mark.parametrize("windows", [False, True])
def test_command_uses_existing_cli_and_never_shell_or_stderr(windows):
    with patch.object(retention.os, "name", "nt" if windows else "posix"), patch.object(
            retention.shutil, "which", return_value="cloud-cli") as which, patch.object(
            retention.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=" {} \n")) as run:
        assert retention.command(["some", "argument"]) == "{}"
        which.assert_called_once_with("gcloud.cmd" if windows else "gcloud")
        assert run.call_args.args[0] == ["cloud-cli", "some", "argument"]
        assert "shell" not in run.call_args.kwargs
    with patch.object(retention.shutil, "which", return_value=None), pytest.raises(RuntimeError, match="unavailable"):
        retention.command([])
    with patch.object(retention.shutil, "which", return_value="cli"), patch.object(
            retention.subprocess, "run", return_value=SimpleNamespace(returncode=7, stderr="private-secret")), pytest.raises(RuntimeError) as error:
        retention.command([])
    assert str(error.value) == "Google Cloud CLI failed (exit 7)"


def test_identifiers_and_remote_snapshot_are_bounded():
    for index in range(5):
        args = ["demo-project", "us-central1", "bots", "zone-a", "instance"]
        args[index] = "bad; echo injected"
        with pytest.raises(ValueError):
            retention.RegistryRetention(*args)
    with patch.object(retention, "command", return_value=json.dumps(snapshot())) as execute:
        assert manager().snapshot() == snapshot()
    args = execute.call_args.args[0]
    assert "--tunnel-through-iap" in args
    encoded = args[-1].split("b64decode('")[1].split("'")[0]
    source = base64.b64decode(encoded).decode()
    assert "read_snapshot(" + repr(PREFIX) + ")" in source
    compile(source, "remote_snapshot", "exec")


@pytest.mark.parametrize("state, message", [({}, "standard Docker"), ({**STATE, "format": "MAVEN"}, "standard Docker"), ({**STATE, "mode": "REMOTE_REPOSITORY"}, "standard Docker"), ({**STATE, "cleanupPolicies": {"other-policy": {}}}, "Unmanaged")])
def test_repository_state_refuses_unsupported_or_unmanaged_policies(state, message):
    with patch.object(retention, "command", return_value=json.dumps(state)), pytest.raises(RuntimeError, match=message):
        manager().repository_state()


def test_repository_state_and_digest_resolution():
    target = manager()
    with patch.object(retention, "command", return_value=json.dumps(STATE)):
        assert target.repository_state() == STATE
    with patch.object(retention, "command", return_value=A) as execute:
        assert target.digest(PREFIX + ":current") == A
        assert target.digest(PREFIX + "@" + A) == A
        execute.assert_called_once()
    assert target.digest(PREFIX + "-other@" + B) == B
    for reference in (PREFIX + "@sha256:bad", PREFIX + ":;bad", PREFIX.replace("/galerazobot", "/unrelated") + ":tag", "https://attacker/image"):
        with pytest.raises(ValueError):
            target.digest(reference)
    with patch.object(retention, "command", return_value=""), pytest.raises(ValueError):
        target.digest(PREFIX + ":missing")


def test_plan_keeps_production_rollback_actual_container_digest_and_candidate():
    target = manager()
    prepare_sync(target)
    policies = target.plan(snapshot(), PREFIX + ":candidate")
    assert policies[0]["condition"]["versionNamePrefixes"] == [value[:64] for value in (A, B, C, "sha256:" + "d" * 64)]
    assert all(len(value) <= 64 for value in policies[0]["condition"]["versionNamePrefixes"])
    assert policies[1]["condition"] == {"tagState": "any", "packageNamePrefixes": ["galerazobot"], "olderThan": "86400s"}
    assert target.expected(policies)[retention.KEEP]["action"] == "KEEP"
    assert target.expected(policies)[retention.DELETE]["condition"]["tagState"] == "ANY"
    empty = {"production": None, "rollback": None, "containers": []}
    with pytest.raises(RuntimeError, match="without any protected"):
        target.plan(empty, None)
    with pytest.raises(ValueError, match="primary bot package"):
        target.plan(empty, PREFIX + "-other:candidate")
    assert target.plan(empty, PREFIX + ":candidate")[0]["condition"]["versionNamePrefixes"] == [("sha256:" + "d" * 64)[:64]]


def test_preview_never_changes_registry():
    target = manager()
    prepare_sync(target)
    assert target.sync()["status"] == "preview"
    target.set_policies.assert_not_called()


def test_runtime_or_configuration_change_aborts_before_mutation():
    target = manager()
    before = prepare_sync(target)
    target.snapshot.side_effect = [before, {**before, "production": PREFIX + ":changed"}]
    with pytest.raises(RuntimeError, match="Runtime changed while planning"):
        target.sync(apply=True)
    target.set_policies.assert_not_called()
    for field, value in (("cleanupPolicies", {}), ("cleanupPolicyDryRun", True)):
        before = prepare_sync(target)
        target.repository_state.side_effect = [STATE, {**STATE, field: value}]
        with pytest.raises(RuntimeError, match="configuration changed"):
            target.sync(apply=True)
        target.set_policies.assert_not_called()
        target.repository_state.side_effect = None


def test_apply_verifies_exact_policy_and_runtime():
    target = manager()
    prepare_sync(target)
    policies = target.plan(snapshot(), None)
    expected = target.expected(policies)
    target.repository_state.side_effect = [STATE, STATE, {**STATE, "cleanupPolicies": expected, "cleanupPolicyDryRun": False}]
    files = []
    target.set_policies.side_effect = lambda filename, **kw: files.append((json.loads(filename.read_text()), kw))
    result = target.sync(apply=True)
    assert result["status"] == "active-verified"
    assert files == [(policies, {"dry_run": False})]


@pytest.mark.parametrize("failure", ["different-policy", "dry-run", "runtime", "unreadable"])
def test_failed_final_verification_pauses_deletions(failure):
    target = manager()
    before = prepare_sync(target)
    actual = {**STATE, "cleanupPolicies": target.expected(target.plan(before, None))}
    if failure == "different-policy":
        actual["cleanupPolicies"] = {}
    if failure == "dry-run":
        actual["cleanupPolicyDryRun"] = True
    target.repository_state.side_effect = [STATE, STATE, RuntimeError("unreadable") if failure == "unreadable" else actual]
    if failure == "runtime":
        target.snapshot.side_effect = [before, before, {**before, "containers": []}]
    with pytest.raises(RuntimeError):
        target.sync(apply=True)
    assert [call.kwargs["dry_run"] for call in target.set_policies.call_args_list] == [False, True]


@pytest.mark.parametrize("with_receipt", [False, True])
def test_main_and_entrypoint_write_only_safe_receipts(tmp_path, with_receipt, capsys):
    result = {"status": "preview", "package": PREFIX, "policies": [{"condition": {"versionNamePrefixes": [A, B]}}]}
    receipt = tmp_path / "receipts" / "retention.json"
    args = ["tool", "--project", "demo-project", "--zone", "zone-a", "--instance", "bot-vm"]
    if with_receipt:
        args += ["--receipt", str(receipt), "--apply", "--candidate", PREFIX + ":candidate"]
    with patch.object(sys, "argv", args), patch.object(retention.RegistryRetention, "sync", return_value=result) as sync:
        assert retention.main() == 0
        assert sync.call_args.kwargs["apply"] == with_receipt
    assert json.loads(capsys.readouterr().out)["protected_roots"] == 2
    if with_receipt:
        assert json.loads(receipt.read_text()) == result


def test_entrypoint_preview_is_fully_offline(capsys):
    def cli(args, **kwargs):
        if args[1:3] == ["compute", "ssh"]:
            data = json.dumps(snapshot())
        elif args[1:4] == ["artifacts", "repositories", "describe"]:
            data = json.dumps(STATE)
        else:
            assert args[1:5] == ["artifacts", "docker", "images", "describe"]
            data = A if args[5].endswith(":current") else B
        return SimpleNamespace(returncode=0, stdout=data)
    args = ["tool", "--project", "demo-project", "--zone", "zone-a", "--instance", "bot-vm"]
    with patch.object(sys, "argv", args), patch.object(retention.shutil, "which", return_value="cli"), patch.object(
            retention.subprocess, "run", side_effect=cli), pytest.raises(SystemExit) as error:
        runpy.run_path(str(Path(retention.__file__)), run_name="__main__")
    assert error.value.code == 0
    assert json.loads(capsys.readouterr().out)["protected_roots"] == 3


def test_policy_cli_dry_run_and_active_flags():
    target = manager()
    with patch.object(retention, "command") as execute:
        target.set_policies("policy.json", dry_run=True)
        target.set_policies("policy.json", dry_run=False)
    assert "--dry-run" in execute.call_args_list[0].args[0]
    assert "--no-dry-run" in execute.call_args_list[1].args[0]


def test_deploy_protects_candidate_before_changes_and_preserves_rollback_on_retry():
    root = Path(__file__).resolve().parents[1]
    ignored = (root / ".dockerignore").read_text().splitlines()
    assert "**/__pycache__/" in ignored
    assert "**/*.pyc" in ignored
    wrapper = (root / "scripts/deploy/Deploy-Gce.ps1").read_text()
    assert wrapper.index("-CandidateImage $Image") < wrapper.index("gcloud compute scp")
    assert wrapper.count("& $retention -ProjectId") == 2
    assert wrapper.rindex("& $retention -ProjectId") > wrapper.index("--command $remoteCommand")
    shell = (root / "deploy/gce/deploy.sh").read_text()
    assert 'if [[ "${old_image}" != "${new_image}" ]]; then\n    cp "${image_env}" "${previous_env}"' in shell
    assert "image prune" not in shell
