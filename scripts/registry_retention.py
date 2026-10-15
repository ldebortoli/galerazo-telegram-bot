"""Protect deployed images before enabling Artifact Registry's daily cleanup."""
from __future__ import annotations

import argparse
import base64
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

KEEP = "galerazo-keep-required"
DELETE = "galerazo-delete-obsolete"
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def read_snapshot(prefix):
    """Read only image references and container metadata; never read bot.env."""
    references = {}
    for role, filename in (("production", "image.env"), ("rollback", "previous-image.env")):
        path = Path("/opt/galerazo") / filename
        values = []
        if path.exists():
            values = [line.partition("=")[2].strip() for line in path.read_text().splitlines()
                      if line.startswith("GALERAZO_IMAGE=")]
            if len(values) != 1 or not values[0].startswith(prefix + ":"):
                raise RuntimeError("Missing or foreign deployed image reference")
        references[role] = values[0] if values else None
    containers = []
    ids = subprocess.check_output(["docker", "ps", "-aq"], text=True).split()
    for container_id in ids:
        item = json.loads(subprocess.check_output(["docker", "inspect", container_id], text=True))[0]
        image = item["Config"]["Image"]
        # Native cleanup uses a package prefix, so cover its entire namespace.
        if image.startswith(prefix):
            local = json.loads(subprocess.check_output(
                ["docker", "image", "inspect", item["Image"]], text=True))[0]
            digests = sorted(value for value in local.get("RepoDigests", [])
                             if value.startswith(prefix))
            if not digests:
                raise RuntimeError("Cannot identify the actual container image digest")
            containers.append({"id": item["Id"], "image": image, "digests": digests,
                               "started": item["State"]["StartedAt"]})
    references["containers"] = sorted(containers, key=lambda item: item["id"])
    if containers and not references["production"]:
        raise RuntimeError("Containers exist without a production reference")
    return references


def command(arguments):
    executable = shutil.which("gcloud.cmd" if os.name == "nt" else "gcloud")
    if not executable:
        raise RuntimeError("Google Cloud CLI is unavailable")
    result = subprocess.run([executable, *arguments], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=180, check=False)
    if result.returncode:
        # CLI stderr is deliberately not copied into receipts or exceptions.
        raise RuntimeError(f"Google Cloud CLI failed (exit {result.returncode})")
    return result.stdout.strip()


class RegistryRetention:
    def __init__(self, project, location, repository, zone, instance):
        for value in (project, location, repository, zone, instance):
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", value):
                raise ValueError("Invalid Google Cloud resource identifier")
        self.project, self.location, self.repository = project, location, repository
        self.zone, self.instance = zone, instance
        self.prefix = f"{location}-docker.pkg.dev/{project}/{repository}/galerazobot"
        self.scope = ["--project", project, "--location", location]

    def snapshot(self):
        source = ("import json, subprocess\nfrom pathlib import Path\n" +
                  inspect.getsource(read_snapshot) + "\nprint(json.dumps(read_snapshot(" +
                  repr(self.prefix) + ")))\n")
        encoded = base64.b64encode(source.encode()).decode()
        remote = "sudo python3 -c \"import base64;exec(base64.b64decode('" + encoded + "'))\""
        return json.loads(command(["compute", "ssh", self.instance, "--project", self.project,
                                   "--zone", self.zone, "--tunnel-through-iap", "--quiet",
                                   "--command", remote]))

    def repository_state(self):
        state = json.loads(command(["artifacts", "repositories", "describe", self.repository,
                                    *self.scope, "--format=json"]))
        if state.get("format") != "DOCKER" or state.get("mode") != "STANDARD_REPOSITORY":
            raise RuntimeError("Cleanup requires a standard Docker repository")
        policies = state.get("cleanupPolicies", {})
        if set(policies) - {KEEP, DELETE}:
            raise RuntimeError("Unmanaged cleanup policies require manual reconciliation")
        return state

    def digest(self, reference):
        pattern = (re.escape(self.prefix) + r"[A-Za-z0-9._/-]*" +
                   r"(?:@sha256:[0-9a-f]{64}|:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})")
        if not re.fullmatch(pattern, reference):
            raise ValueError("Image does not belong to the managed package namespace")
        if "@" in reference:
            value = reference.rpartition("@")[2]
        else:
            value = command(["artifacts", "docker", "images", "describe", reference,
                             "--project", self.project, "--format=value(image_summary.digest)"])
        if not DIGEST.fullmatch(value):
            raise ValueError("Image digest is missing or invalid")
        return value

    def plan(self, snapshot, candidate):
        references = [value for role in ("production", "rollback") if (value := snapshot[role])]
        for container in snapshot["containers"]:
            references.extend([container["image"], *container["digests"]])
        if candidate:
            if not candidate.startswith((self.prefix + ":", self.prefix + "@")):
                raise ValueError("Candidate must belong to the primary bot package")
            references.append(candidate)
        # The API limits version prefixes to 64 characters (sha256: uses seven).
        # A shared 228-bit prefix only retains extra content; never removes a root.
        digests = sorted({self.digest(ref)[:64] for ref in references})
        if not digests:
            raise RuntimeError("Refusing cleanup without any protected image")
        # Google also preserves children referenced by a retained parent manifest.
        return [
            {"name": KEEP, "action": {"type": "Keep"}, "condition": {
                "tagState": "any", "packageNamePrefixes": ["galerazobot"],
                "versionNamePrefixes": digests}},
            {"name": DELETE, "action": {"type": "Delete"}, "condition": {
                "tagState": "any", "packageNamePrefixes": ["galerazobot"],
                "olderThan": "86400s"}},
        ]

    @staticmethod
    def expected(policies):
        return {item["name"]: {"id": item["name"], "action": item["action"]["type"].upper(),
                               "condition": {**item["condition"], "tagState": "ANY"}}
                for item in policies}

    def set_policies(self, filename, *, dry_run):
        command(["artifacts", "repositories", "set-cleanup-policies", self.repository,
                 *self.scope, "--policy", str(filename),
                 "--dry-run" if dry_run else "--no-dry-run", "--quiet"])

    def sync(self, *, candidate=None, apply=False):
        before = self.snapshot()
        state = self.repository_state()
        policies = self.plan(before, candidate)
        if self.snapshot() != before:
            raise RuntimeError("Runtime changed while planning; cleanup was not modified")
        receipt = {"package": self.prefix, "runtime": before, "policies": policies,
                   "status": "preview", "grace_seconds": 86400}
        if not apply:
            return receipt
        fresh = self.repository_state()
        for field in ("cleanupPolicies", "cleanupPolicyDryRun"):
            if fresh.get(field) != state.get(field):
                raise RuntimeError("Cleanup configuration changed while planning")
        with tempfile.TemporaryDirectory(prefix="galerazo-retention-") as folder:
            filename = Path(folder) / "policies.json"
            filename.write_text(json.dumps(policies), encoding="utf-8")
            self.set_policies(filename, dry_run=False)
            try:
                actual = self.repository_state()
                if (actual.get("cleanupPolicies") != self.expected(policies)
                        or actual.get("cleanupPolicyDryRun", False)):
                    raise RuntimeError("Cleanup configuration did not match the requested policy")
                if self.snapshot() != before:
                    raise RuntimeError("Runtime changed during cleanup configuration")
            except Exception:
                # Pause deletion if the final runtime/configuration cannot be verified.
                self.set_policies(filename, dry_run=True)
                raise
        receipt["status"] = "active-verified"
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("project", "zone", "instance"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--repository", default="bots")
    parser.add_argument("--candidate")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    manager = RegistryRetention(args.project, args.location, args.repository, args.zone, args.instance)
    result = manager.sync(candidate=args.candidate, apply=args.apply)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "package": result["package"],
                      "protected_roots": len(result["policies"][0]["condition"]["versionNamePrefixes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
