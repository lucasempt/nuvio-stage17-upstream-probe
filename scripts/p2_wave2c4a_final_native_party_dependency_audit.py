#!/usr/bin/env python3
"""Stage17 P2 Wave2C4a: read-only native Watch Party dependency audit.

Inspect ONLY a disposable checkout of the pinned PUBLIC NuvioMedia/NuvioMobile
source, after all approved cumulative patches through Wave2C3b. Does not
rewrite/delete files, compile, access private repositories, or upload artifacts.
Outputs file/line/symbol metadata (never source lines or private data).
"""

import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
TEST_BASE = "composeApp/src/commonTest/kotlin/com/nuvio/app/"
PARTY_DIR = BASE + "features/party/"
PARTY_TEST_DIR = TEST_BASE + "features/party/"
BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
MAIN = BASE + "MainAppContent.kt"
NAV = BASE + "AppNavigationSupport.kt"
ROUTES = BASE + "navigation/Routes.kt"
DEEPLINK = BASE + "core/deeplink/AppUrlBridge.kt"
DEEPLINK_TEST = TEST_BASE + "core/deeplink/AppUrlBridgeTest.kt"
STATE = BASE + "features/player/PlayerScreenRuntimeState.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"

PREVIOUS = {BASE + rel for rel in (
    "SettingsDestinations.kt", "AppShellComponents.kt", "MainAppContent.kt",
    "features/settings/SettingsScreen.kt", "features/settings/SettingsRootPage.kt",
    "StreamDestination.kt", "features/player/PlayerScreenRuntimeUi.kt",
    "features/player/PlayerScreenRuntimeGestureActions.kt",
    "features/player/PlayerScreenRuntimeEffects.kt", "features/player/PlayerControls.kt",
    "features/player/PlayerControlActions.kt",
    "features/player/PlayerScreenRuntimePlaybackActions.kt",
    "features/player/PlayerScreenRuntimeState.kt",
    "features/player/PlayerScreenRuntimeParty.kt",
    "PlayerDestination.kt", "features/player/PlayerScreen.kt",
    "features/player/PlayerScreenArgs.kt", "AppNavigationSupport.kt",
    "navigation/Routes.kt",
)}
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
SYMBOLS = re.compile(
    r"\b(?:PartyRepository|PartyRoute|PartyMedia|PartySync|PartyScreen|"
    r"PartyStream|PartySource|PartyEvent|PartyPanel|PartyPresence|"
    r"PARTY_CODE_LENGTH|normalizePartyCode|isValidPartyCode|formatPartyCode|"
    r"partyMediaKey|partyDeepLink|onOpenPartyMedia|openPartyMedia|watchPartyTitle)\b"
)
IMPORT = re.compile(r"^\s*import\s+com\.nuvio\.app\.features\.party(?:\.([A-Za-z_][A-Za-z0-9_]*|\*))?\s*$")
FULLY_QUALIFIED = re.compile(r"\bcom\.nuvio\.app\.features\.party(?:\.|\b)")
DEEPLINK_PARTY = re.compile(r"\bAppDeepLink\.Party\b")
RESOURCE_REF = re.compile(r"\b(?:Res\.string|R\.string)\.party_[A-Za-z0-9_]+\b")
NON_KOTLIN_EXTENSIONS = {".xml", ".swift", ".plist", ".kts", ".gradle", ".properties", ".json", ".toml"}
NON_KOTLIN_PARTY = re.compile(
    r"\bparty(?:_|[A-Z]|/|-)|\bfeatures\.party\b|nuvio://party|nuvio\.tv/party",
    re.IGNORECASE,
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit("REFUSE_P2_WAVE2C4A: " + reason)


def checked_file(root: Path, rel: str) -> Path:
    p = root / rel
    require(p.is_file() and not p.is_symlink(), "missing/unsafe public file: " + rel)
    return p


def read(root: Path, rel: str) -> str:
    return checked_file(root, rel).read_text(encoding="utf-8")


def audit(root: Path) -> dict:
    kt_paths = sorted(
        p for p in git(root, "ls-files", "--", "*.kt").splitlines()
        if p.startswith("composeApp/src/") and (root / p).is_file()
    )
    require(len(kt_paths) >= 1000, "unexpectedly small tracked public Kotlin tree")
    require(BRIDGE not in kt_paths or not (root / BRIDGE).exists(),
            "removed player Party bridge unexpectedly exists")
    party_files = [p for p in kt_paths if p.startswith(PARTY_DIR)]
    party_tests = [p for p in kt_paths if p.startswith(PARTY_TEST_DIR)]
    require(len(party_files) >= 10, "native Party core missing before removal audit")
    require(len(party_tests) >= 2, "native Party tests missing before audit")
    require(DEEPLINK in kt_paths and DEEPLINK_TEST in kt_paths,
            "app link implementation/tests absent")

    imports = []
    external_symbols = []
    deeplink_use = []
    resources = []
    for rel in kt_paths:
        if rel.startswith(PARTY_DIR) or rel.startswith(PARTY_TEST_DIR):
            continue
        content = read(root, rel)
        for n, line in enumerate(content.splitlines(), 1):
            m = IMPORT.match(line)
            if m:
                imports.append((rel, n, m.group(1) or "<package>"))
            if FULLY_QUALIFIED.search(line) and not m:
                external_symbols.append((rel, n, "qualified-party-package"))
            # Imports are recorded separately to avoid duplicate reporting.
            if not m:
                for symbol in sorted(set(SYMBOLS.findall(line))):
                    external_symbols.append((rel, n, symbol))
            if DEEPLINK_PARTY.search(line):
                deeplink_use.append((rel, n))
            for resource in sorted(set(RESOURCE_REF.findall(line))):
                resources.append((rel, n, resource))

    # All lines returned are bounded public path/symbol metadata, not raw code.
    require(len(imports) <= 100 and len(external_symbols) <= 300
            and len(deeplink_use) <= 100 and len(resources) <= 300,
            "unusually large audit result; inspect scanner before expanding")
    # Non-Kotlin references are an informational cleanup inventory; no source is modified.
    non_kotlin = []
    skipped_large = []
    for rel in git(root, "ls-files").splitlines():
        path = root / rel
        if path.suffix.lower() not in NON_KOTLIN_EXTENSIONS or not path.is_file() or path.is_symlink():
            continue
        if path.stat().st_size > 2_000_000:
            skipped_large.append(rel)
            continue
        matches = len(NON_KOTLIN_PARTY.findall(path.read_text(encoding="utf-8", errors="replace")))
        if matches:
            non_kotlin.append((rel, matches))
    return {
        "non_kotlin": sorted(non_kotlin),
        "skipped_large": sorted(skipped_large),
        "kotlin_scanned": len(kt_paths),
        "party_core": party_files,
        "party_tests": party_tests,
        "imports": sorted(imports),
        "external_symbols": sorted(set(external_symbols)),
        "deeplinks": sorted(deeplink_use),
        "resources": sorted(resources),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    root = parser.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED, "wrong frozen public upstream")
    require(not git(root, "diff", "--cached", "--name-only"), "staged changes present")
    changed = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(changed), "cumulative patches through Wave2C3b not applied")
    require(changed.issubset(PREVIOUS | ALLOWED_GITLINKS), "unapproved changed files")
    require(not (root / BRIDGE).exists(), "legacy player Party bridge still exists")
    require("PartyRoute" not in read(root, NAV) + read(root, ROUTES),
            "Wave2C3a PartyRoute still present")
    main = read(root, MAIN)
    require("PartyRepository" not in main and "PartyRoute" not in main,
            "Wave2C3b orphan Party references still in MainApp")
    require("is AppDeepLink.Party ->" in main,
            "legacy invite branch unexpectedly removed")
    require("showPartyPanel" not in read(root, STATE), "old player Party state remains")
    require("currentNormalPlaybackPositionMs" in read(root, PLAYBACK),
            "normal player position helper missing")
    deep = read(root, DEEPLINK)
    require("internal fun parseAppDeepLink" in deep and "AppDeepLink.Party" in deep,
            "public deep-link parser unexpectedly changed")

    before = subprocess.check_output([
        "git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=normal"
    ])
    data = audit(root)
    after = subprocess.check_output([
        "git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=normal"
    ])
    require(before == after, "read-only audit changed worktree")
    print("P2_WAVE2C4A_PUBLIC_READ_ONLY_AUDIT=PASS")
    print("P2_WAVE2C4A_PINNED_UPSTREAM=PASS")
    print(f"P2_WAVE2C4A_KOTLIN_FILES_SCANNED={data['kotlin_scanned']}")
    print(f"P2_WAVE2C4A_NATIVE_PARTY_CORE_FILES={len(data['party_core'])}")
    print(f"P2_WAVE2C4A_NATIVE_PARTY_TEST_FILES={len(data['party_tests'])}")
    for p in data["party_core"]:
        print("P2_WAVE2C4A_NATIVE_CORE_FILE=" + p)
    for p in data["party_tests"]:
        print("P2_WAVE2C4A_NATIVE_TEST_FILE=" + p)
    for key, field in (
        ("EXTERNAL_IMPORT", "imports"),
        ("EXTERNAL_SYMBOL", "external_symbols"),
        ("DEEPLINK_REFERENCE", "deeplinks"),
        ("PARTY_RESOURCE_REFERENCE", "resources"),
    ):
        rows = data[field]
        print(f"P2_WAVE2C4A_{key}_COUNT={len(rows)}")
        for row in rows:
            print("P2_WAVE2C4A_" + key + "=" + ":".join(map(str, row)))
    print(f"P2_WAVE2C4A_NON_KOTLIN_PARTY_FILES={len(data['non_kotlin'])}")
    for path, count in data["non_kotlin"][:90]:
        print(f"P2_WAVE2C4A_NON_KOTLIN_PARTY_FILE={path}:occurrences={count}")
    if len(data["non_kotlin"]) > 90:
        print(f"P2_WAVE2C4A_NON_KOTLIN_PARTY_FILES_NOT_LISTED={len(data['non_kotlin'])-90}")
    print(f"P2_WAVE2C4A_LARGE_TEXT_FILES_SKIPPED={len(data['skipped_large'])}")
    for path in data["skipped_large"]:
        print("P2_WAVE2C4A_SKIPPED_LARGE_TEXT_FILE=" + path)
    blocker = bool(data["imports"] or data["external_symbols"])
    print("P2_WAVE2C4A_NATIVE_MODULE_DELETE_NOW=" +
          ("BLOCKED_NEEDS_PUBLIC_DETACH" if blocker else "NEEDS_SEPARATE_VALIDATION"))
    print("P2_WAVE2C4A_NO_PRIVATE_TOGETHER_CODE=YES")
    print("P2_WAVE2C4A_NO_FILES_CHANGED=YES")
    print("P2_WAVE2C4A_NO_APK_BUILD=YES")

if __name__ == "__main__":
    main()
