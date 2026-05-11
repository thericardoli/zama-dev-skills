#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "zama-dev-skills-upstream-check"


def main() -> None:
    args = parse_args()
    now = utc_now()
    state = read_json(args.state, default={"version": 1, "last_checked_at": None, "sources": {}})

    if not args.force and not should_check(state.get("last_checked_at"), args.interval_days, now):
        summary = {
            "skipped": True,
            "has_updates": False,
            "checked_at": isoformat(now),
            "issue_title": "",
            "reason": f"Last check was less than {args.interval_days} day(s) ago.",
        }
        write_json(args.summary, summary)
        args.report.write_text(render_skipped_report(summary), encoding="utf-8")
        print(summary["reason"])
        return

    config = read_yaml(args.sources)
    sources = config.get("sources")
    if not isinstance(sources, list):
        raise SystemExit("upstream sources file must contain a `sources` list")

    old_sources = state.get("sources") if isinstance(state.get("sources"), dict) else {}
    current_sources: dict[str, dict[str, Any]] = {}
    updates: list[dict[str, Any]] = []
    bootstrapped: list[dict[str, Any]] = []

    for raw_source in sources:
        if not isinstance(raw_source, dict):
            raise SystemExit("each upstream source must be a mapping")
        if raw_source.get("enabled", True) is False:
            continue

        source_id = require_str(raw_source, "id")
        snapshot = fetch_snapshot(raw_source)
        current_sources[source_id] = snapshot

        previous = old_sources.get(source_id)
        if not isinstance(previous, dict):
            bootstrapped.append({"source": raw_source, "current": snapshot})
            continue

        if str(previous.get("version")) != str(snapshot.get("version")):
            updates.append(
                {
                    "source": raw_source,
                    "previous": previous,
                    "current": snapshot,
                    "compare_url": build_compare_url(raw_source, previous, snapshot),
                }
            )

    next_state = {
        "version": 1,
        "last_checked_at": isoformat(now),
        "sources": current_sources,
    }
    write_json(args.state, next_state)

    report = render_report(updates=updates, bootstrapped=bootstrapped, checked_at=now)
    args.report.write_text(report, encoding="utf-8")

    summary = {
        "skipped": False,
        "has_updates": bool(updates),
        "checked_at": isoformat(now),
        "issue_title": make_issue_title(updates),
        "updates": len(updates),
        "bootstrapped": len(bootstrapped),
    }
    write_json(args.summary, summary)

    if updates:
        print(f"Detected {len(updates)} upstream update(s).")
    else:
        print("No upstream updates detected.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check upstream Zama sources for updates.")
    parser.add_argument("--sources", type=Path, default=Path("upstream-sources.yaml"))
    parser.add_argument("--state", type=Path, default=Path("upstream-state.json"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--interval-days", type=int, default=5)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required. Install it with `python -m pip install PyYAML`.") from exc

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"YAML file must contain a mapping: {path}")
    return data


def read_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"JSON file must contain an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def should_check(last_checked_at: Any, interval_days: int, now: datetime) -> bool:
    if not last_checked_at:
        return True
    try:
        last = parse_time(str(last_checked_at))
    except ValueError:
        return True
    return now - last >= timedelta(days=interval_days)


def fetch_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    kind = require_str(source, "kind")
    if kind == "github-release":
        return fetch_github_release(source)
    if kind == "github-branch":
        return fetch_github_branch(source)
    if kind == "npm":
        return fetch_npm(source)
    raise SystemExit(f"Unsupported upstream source kind `{kind}` for `{source.get('id')}`")


def fetch_github_release(source: dict[str, Any]) -> dict[str, Any]:
    repo = require_str(source, "repo")
    data = request_json(f"https://api.github.com/repos/{repo}/releases/latest")
    tag_name = require_response_str(data, "tag_name", source)
    return {
        "kind": "github-release",
        "repo": repo,
        "version": tag_name,
        "name": data.get("name") or tag_name,
        "url": data.get("html_url") or f"https://github.com/{repo}/releases/tag/{tag_name}",
        "published_at": data.get("published_at"),
    }


def fetch_github_branch(source: dict[str, Any]) -> dict[str, Any]:
    repo = require_str(source, "repo")
    branch = str(source.get("branch") or "main")
    data = request_json(
        f"https://api.github.com/repos/{repo}/branches/{urllib.parse.quote(branch, safe='')}"
    )
    commit = data.get("commit")
    if not isinstance(commit, dict):
        raise SystemExit(f"GitHub branch response for `{repo}@{branch}` has no commit object")
    sha = require_response_str(commit, "sha", source)
    short_sha = sha[:12]
    return {
        "kind": "github-branch",
        "repo": repo,
        "branch": branch,
        "version": sha,
        "name": f"{branch}@{short_sha}",
        "url": f"https://github.com/{repo}/commit/{sha}",
    }


def fetch_npm(source: dict[str, Any]) -> dict[str, Any]:
    package = require_str(source, "package")
    encoded = urllib.parse.quote(package, safe="")
    data = request_json(f"https://registry.npmjs.org/{encoded}")
    dist_tags = data.get("dist-tags")
    if not isinstance(dist_tags, dict):
        raise SystemExit(f"npm response for `{package}` has no dist-tags object")
    latest = dist_tags.get("latest")
    if not isinstance(latest, str) or not latest:
        raise SystemExit(f"npm response for `{package}` has no latest dist-tag")

    versions = data.get("versions")
    published_at = None
    if isinstance(versions, dict):
        version_data = versions.get(latest)
        if isinstance(version_data, dict):
            time_data = data.get("time")
            if isinstance(time_data, dict):
                published_at = time_data.get(latest)

    return {
        "kind": "npm",
        "package": package,
        "version": latest,
        "name": f"{package}@{latest}",
        "url": f"https://www.npmjs.com/package/{encoded}",
        "published_at": published_at,
    }


def request_json(url: str) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json",
        "User-Agent": USER_AGENT,
    }
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Request failed for {url}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Request failed for {url}: {exc.reason}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Expected JSON object from {url}")
    return data


def build_compare_url(
    source: dict[str, Any], previous: dict[str, Any], current: dict[str, Any]
) -> str | None:
    kind = source.get("kind")
    old_version = previous.get("version")
    new_version = current.get("version")
    if not old_version or not new_version:
        return None
    if kind in {"github-release", "github-branch"}:
        repo = source.get("repo")
        if isinstance(repo, str) and repo:
            return f"https://github.com/{repo}/compare/{old_version}...{new_version}"
    return None


def render_report(
    *,
    updates: list[dict[str, Any]],
    bootstrapped: list[dict[str, Any]],
    checked_at: datetime,
) -> str:
    lines = [
        "# Upstream Updates Detected",
        "",
        f"Checked at: `{isoformat(checked_at)}`",
        "",
    ]

    if not updates:
        lines.extend(["No upstream updates were detected.", ""])
    else:
        lines.extend(
            [
                "The following upstream source(s) changed since the last recorded check.",
                "Please review the affected skills and rerun relevant eval tasks before updating the skill content.",
                "",
            ]
        )
        for item in updates:
            source = item["source"]
            previous = item["previous"]
            current = item["current"]
            lines.extend(
                [
                    f"## {source['id']}",
                    "",
                    f"- Kind: `{source['kind']}`",
                    f"- Previous: `{previous.get('name') or previous.get('version')}`",
                    f"- Current: `{current.get('name') or current.get('version')}`",
                    f"- Current URL: {current.get('url')}",
                ]
            )
            if item.get("compare_url"):
                lines.append(f"- Compare: {item['compare_url']}")
            affects = source.get("affects")
            if isinstance(affects, list) and affects:
                lines.append("- Affected skills:")
                lines.extend(f"  - `{path}`" for path in affects)
            lines.append("")

    if bootstrapped:
        lines.extend(["## Newly Tracked Sources", ""])
        lines.append(
            "These sources did not exist in the previous state file, so they were bootstrapped without creating update findings."
        )
        lines.append("")
        for item in bootstrapped:
            source = item["source"]
            current = item["current"]
            lines.append(f"- `{source['id']}`: `{current.get('name') or current.get('version')}`")
        lines.append("")

    lines.extend(
        [
            "## Suggested Follow-Up",
            "",
            "- Review release notes, compare links, and changed API/type definitions.",
            "- Update affected `SKILL.md` and `references/` files only where the upstream behavior actually changed.",
            "- Run at least one representative eval task after making skill updates.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_skipped_report(summary: dict[str, Any]) -> str:
    return (
        "# Upstream Check Skipped\n\n"
        f"Checked at: `{summary['checked_at']}`\n\n"
        f"Reason: {summary['reason']}\n"
    )


def make_issue_title(updates: list[dict[str, Any]]) -> str:
    if not updates:
        return ""
    if len(updates) == 1:
        source = updates[0]["source"]
        current = updates[0]["current"]
        return f"[upstream] {source['id']} updated to {current.get('name') or current.get('version')}"
    return f"[upstream] {len(updates)} Zama-related sources updated"


def require_str(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"source `{mapping.get('id', '<unknown>')}` must define `{key}`")
    return value.strip()


def require_response_str(
    mapping: dict[str, Any], key: str, source: dict[str, Any]
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"response for source `{source.get('id')}` did not include `{key}`")
    return value.strip()


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


if __name__ == "__main__":
    main()
