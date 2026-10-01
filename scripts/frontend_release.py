"""Fixed frontend release bridge used by Bot Control Center (no bot mutations)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DOMAINS = ("https://galerazo.com", "https://www.galerazo.com")
REMOTE = "https://github.com/ldebortoli/galerazo-web"
PATHS = ("app", "lib", "miniapp", "public", "worker", "scripts", ".openai/hosting.json", "vite.config.ts", "next.config.ts", "package.json", "package-lock.json", "tsconfig.json", "release-contract.json")
FEATURES = {"shared-album-s1", "own-view", "club-90-days"}
REMOTE_HEALTH = """set -eu
container_id=$(sudo docker compose --env-file /opt/galerazo/image.env -f /opt/galerazo/compose.yaml ps -q bot)
test -n "$container_id"
sudo docker inspect --format '{{json .State}}' "$container_id"
sudo docker inspect --format '{{.Config.Image}}' "$container_id"
sudo docker exec "$container_id" python -c 'from galerazo_bot.versioning import CURRENT_VERSION; print(CURRENT_VERSION)'
"""


def command(args, *, cwd=None):
    args = list(args)
    if args[0] == "gcloud" and os.name == "nt":
        gcloud = Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"
        if not gcloud.is_file():
            raise RuntimeError("Existing Google Cloud CLI is unavailable")
        args[0] = str(gcloud)
        args[-1] = args[-1].replace("\n", "; ").rstrip("; ")
    environment = {**os.environ, "CI": "true", "WRANGLER_WRITE_LOGS": "false", "WRANGLER_SEND_METRICS": "false"}
    result = subprocess.run(args, cwd=cwd, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, check=False)
    if result.returncode:
        # Neither gcloud nor npm output is a safe source for credentials in errors.
        raise RuntimeError(f"{Path(args[0]).name} failed (exit {result.returncode})")
    return result.stdout.strip()


def http(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 GalerazoRelease", "Cache-Control": "no-cache"})
    try:
        with urlopen(request, timeout=20) as response:
            return response.status, response.read(65537), dict(response.headers)
    except HTTPError as error:
        return error.code, error.read(65537), dict(error.headers)


def version(value):
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value):
        raise ValueError("Invalid release version")
    parts = tuple(map(int, value.split(".")))
    return parts + (0,) * (3 - len(parts))


def compatible(metadata, bot_version):
    if metadata.get("schema") != 1 or not re.fullmatch(r"[a-f0-9]{40}", metadata.get("commit", "")) or not re.fullmatch(r"[a-f0-9]{64}", metadata.get("fingerprint", "")):
        raise RuntimeError("Missing or invalid frontend release metadata")
    if version(bot_version) < version(metadata["minimum_bot_version"]):
        raise RuntimeError("Frontend requires a newer bot")
    if version(bot_version) >= version("0.65") and not FEATURES.issubset(metadata.get("features", [])):
        raise RuntimeError("Frontend cannot handle the bot album contract")


class FrontendRelease:
    def __init__(self, repository, project, zone, instance, *, run=command, get=http, sleep=time.sleep):
        self.repository = Path(repository).resolve()
        self.project, self.zone, self.instance = project, zone, instance
        for value in (project, zone, instance):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value):
                raise ValueError("Invalid GCE identifier")
        self.run, self.get, self.sleep = run, get, sleep

    def git(self, *args, cwd=None):
        return self.run(["git", *args], cwd=cwd or self.repository)

    def backend(self, expected_image=None):
        lines = self.run(["gcloud", "compute", "ssh", self.instance, "--project", self.project, "--zone", self.zone, "--tunnel-through-iap", "--quiet", "--command", REMOTE_HEALTH]).splitlines()
        state, image, bot_version = json.loads(lines[-3]), lines[-2], lines[-1]
        if not state.get("Running") or state.get("Health", {}).get("Status") != "healthy":
            raise RuntimeError("Bot is not healthy; frontend release stopped")
        if expected_image and image != expected_image:
            raise RuntimeError("The active bot image does not match the release")
        version(bot_version)
        return bot_version, image

    def metadata(self, domain, *, legacy=False):
        status, body, _ = self.get(domain + "/miniapp/release.json")
        if status == 404 and legacy:
            # Only a confirmed old document may bootstrap the first deployment.
            status, body, _ = self.get(domain + "/miniapp")
            if status == 200 and b"?v=0.1.10" in body:
                return None
        if status != 200 or len(body) > 65536:
            raise RuntimeError("Frontend release metadata unavailable")
        return json.loads(body)

    def verify(self, plan, *, expected_image=None):
        bot_version, image = self.backend(expected_image)
        for domain in DOMAINS:
            metadata = self.metadata(domain)
            compatible(metadata, bot_version)
            if metadata != plan["metadata"]:
                raise RuntimeError("Served frontend does not match the selected source")
            status, html, _ = self.get(domain + "/miniapp")
            if status != 200 or ("?v=" + metadata["version"]).encode() not in html:
                raise RuntimeError("Mini App document version mismatch")
            for filename, digest in plan["assets"].items():
                status, data, _ = self.get(domain + "/miniapp-assets/" + filename + "?v=" + metadata["version"])
                if status != 200 or hashlib.sha256(data).hexdigest() != digest:
                    raise RuntimeError("Served Mini App asset mismatch")
            status, body, headers = self.get(domain + "/miniapp/api/bootstrap")
            if status != 401 or json.loads(body).get("error") != "telegram_required" or headers.get("Cache-Control", headers.get("cache-control")) != "no-store":
                raise RuntimeError("Unauthenticated gateway is not closed")
        return {"bot_version": bot_version, "bot_image": image, "frontend_commit": plan["metadata"]["commit"], "frontend_version": plan["metadata"]["version"]}

    def sync(self, target_bot_version):
        if self.git("remote", "get-url", "origin").removesuffix(".git") != REMOTE:
            raise RuntimeError("Unexpected frontend repository")
        if self.git("status", "--porcelain=v1", "--untracked-files=normal"):
            raise RuntimeError("Frontend has uncommitted changes; release stopped")
        if self.git("symbolic-ref", "--short", "HEAD") != "main":
            raise RuntimeError("Frontend must be on main")
        self.git("fetch", "--prune", "origin", "main")
        local = self.git("rev-parse", "refs/heads/main")
        remote = self.git("rev-parse", "refs/remotes/origin/main")
        if local != remote:
            # Never publish unpushed frontend code. Fast-forward remote work is safe.
            self.git("merge-base", "--is-ancestor", local, remote)
        target = remote
        bot_version, _ = self.backend()
        source = self.git("ls-tree", "-r", target, "--", *PATHS)
        fingerprint = hashlib.sha256((source + "\n").encode()).hexdigest()
        published = [self.metadata(domain, legacy=True) for domain in DOMAINS]
        changed = any(item is None or item.get("fingerprint") != fingerprint for item in published)
        with tempfile.TemporaryDirectory(prefix="galerazo-frontend-") as temporary:
            snapshot = Path(temporary) / "source"
            self.git("worktree", "add", "--detach", str(snapshot), target)
            try:
                contract = json.loads((snapshot / "release-contract.json").read_text(encoding="utf-8"))
                manifest = json.loads((snapshot / "package.json").read_text(encoding="utf-8"))
                metadata = {**contract, "commit": target, "fingerprint": fingerprint, "version": manifest["version"]}
                compatible(metadata, target_bot_version)
                compatible(metadata, bot_version)
                assets = {name: hashlib.sha256((snapshot / "public/miniapp-assets" / name).read_bytes()).hexdigest() for name in ("app.js", "core.js", "styles.css")}
                if not changed:
                    # A docs-only commit keeps the real deployed commit as its provenance.
                    metadata = published[0]
                plan = {"changed": changed, "metadata": metadata, "assets": assets}
                if changed:
                    node = shutil.which("node")
                    if not node:
                        raise RuntimeError("Node.js is required for the frontend")
                    npm = Path(node).parent / "node_modules/npm/bin/npm-cli.js"
                    if not npm.is_file():
                        raise RuntimeError("npm CLI is unavailable beside Node.js")
                    for arguments in (("ci", "--no-fund", "--no-audit"), ("run", "check"), ("run", "coverage"), ("run", "build"), ("test",)):
                        print("Frontend: npm " + " ".join(arguments), flush=True)
                        self.run([node, str(npm), *arguments], cwd=snapshot)
                    wrangler = [node, str(snapshot / "node_modules/wrangler/bin/wrangler.js")]
                    self.run([*wrangler, "deploy", "--dry-run", "--config", "dist/server/wrangler.json"], cwd=snapshot)
                    # Guard against accidental changes from lifecycle hooks or tools.
                    if self.git("status", "--porcelain=v1", "--untracked-files=normal", cwd=snapshot):
                        raise RuntimeError("Frontend validation modified tracked source")
                    output = self.run([*wrangler, "deploy", "--config", "dist/server/wrangler.json", "--domain", "galerazo.com", "--domain", "www.galerazo.com", "--tag", target[:12], "--message", "Galerazo source " + target], cwd=snapshot)
                    match = re.search(r"Current Version ID: ([a-f0-9-]{36})", output)
                    if match:
                        print("Cloudflare Worker version: " + match[1], flush=True)
                # Allow bounded propagation only; every subsequent run reads reality.
                for attempt in range(6):
                    try:
                        evidence = self.verify(plan)
                        break
                    except (RuntimeError, OSError, ValueError):
                        if attempt == 5:
                            raise
                        self.sleep(5)
                return {**plan, **evidence}
            finally:
                self.git("worktree", "remove", "--force", str(snapshot))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("sync", "verify"), required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--zone", required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--target-bot-version")
    parser.add_argument("--expected-image")
    args = parser.parse_args()
    release = FrontendRelease(args.repository, args.project, args.zone, args.instance)
    if args.stage == "sync":
        if not args.target_bot_version:
            parser.error("sync requires --target-bot-version")
        result = release.sync(args.target_bot_version)
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else:
        result = release.verify(json.loads(args.result.read_text(encoding="utf-8")), expected_image=args.expected_image)
    print(json.dumps({key: result[key] for key in ("bot_version", "bot_image", "frontend_commit", "frontend_version")}, sort_keys=True))


if __name__ == "__main__":
    main()
