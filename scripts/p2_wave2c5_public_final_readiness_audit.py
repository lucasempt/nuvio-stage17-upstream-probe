#!/usr/bin/env python3
"""Stage17 P2 Wave2C5: READ-ONLY final audit of the frozen PUBLIC migration.

Execute after cumulative public P2 patches through Wave2C4d, inside a disposable
checkout of the frozen upstream. This audits source and tracked changes ONLY.
It does not build, write files, access the private Together repository or
claim private Together functionality works.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
TEST_BASE = "composeApp/src/commonTest/kotlin/com/nuvio/app/"
PARTY_CORE = BASE + "features/party/"
PARTY_TEST = TEST_BASE + "features/party/"
DEEP_LINK = BASE + "core/deeplink/AppUrlBridge.kt"
DEEP_LINK_TEST = TEST_BASE + "core/deeplink/AppUrlBridgeTest.kt"
MAIN = BASE + "MainAppContent.kt"
NAV = BASE + "AppNavigationSupport.kt"
ROUTES = BASE + "navigation/Routes.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"
PLAYER_BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
MANIFEST = "androidApp/src/main/AndroidManifest.xml"
OLD_STRINGS = "composeApp/src/commonMain/composeResources/values/strings_party.xml"

MANIFEST_BLOB = "a73b22ab63c98e6e8f552c1adec791086eca28d2"
DEEP_LINK_TEST_BLOB = "a1e48f97e9df99e3f44e490478c099ed367a9244"
OLD_STRINGS_BLOB = "426af4690a4425f02f75f81674998a8b498421a0"
EXPECTED_KOTLIN_JAVA = 1247
EXPECTED_TEXT_SOURCE_RESOURCE_FILES = 1397
CORE_NAMES = (
    "PartyApi.kt", "PartyChannel.kt", "PartyClock.kt", "PartyCode.kt",
    "PartyDetails.kt", "PartyModels.kt", "PartyPanel.kt", "PartyRepository.kt",
    "PartyScreen.kt", "PartySourceMatch.kt", "PartySync.kt", "PartyUi.kt",
)
TEST_NAMES = ("PartyStreamTest.kt", "PartySyncTest.kt")
PARTY_FILES = {PARTY_CORE + n for n in CORE_NAMES} | {PARTY_TEST + n for n in TEST_NAMES}
DELETED = PARTY_FILES | {PLAYER_BRIDGE, OLD_STRINGS}
# Approved cumulative public patch footprint, frozen at Wave2C4d.
UPDATED = {BASE + p for p in (
    "SettingsDestinations.kt", "AppShellComponents.kt", "MainAppContent.kt",
    "features/settings/SettingsScreen.kt", "features/settings/SettingsRootPage.kt",
    "StreamDestination.kt", "features/player/PlayerScreenRuntimeUi.kt",
    "features/player/PlayerScreenRuntimeGestureActions.kt",
    "features/player/PlayerScreenRuntimeEffects.kt", "features/player/PlayerControls.kt",
    "features/player/PlayerControlActions.kt",
    "features/player/PlayerScreenRuntimePlaybackActions.kt",
    "features/player/PlayerScreenRuntimeState.kt",
    "PlayerDestination.kt", "features/player/PlayerScreen.kt",
    "features/player/PlayerScreenArgs.kt", "AppNavigationSupport.kt",
    "navigation/Routes.kt", "core/deeplink/AppUrlBridge.kt",
)}
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
SCANNABLE_SUFFIXES = {
    ".kt", ".java", ".xml", ".swift", ".plist", ".kts",
    ".gradle", ".properties", ".toml", ".json", ".js", ".ts", ".tsx",
}
OLD_PARTY_REFERENCES = re.compile(
    r"\b(?:PartyRepository|PartyRoute|PartyMedia|PartySync|PartyScreen|"
    r"PartyStream|PartySource|PartyEvent|PartyPanel|PartyPresence|"
    r"PARTY_CODE_LENGTH|normalizePartyCode|isValidPartyCode|formatPartyCode|"
    r"partyMediaKey|partyDeepLink|onOpenPartyMedia|openPartyMedia|watchPartyTitle)\b"
)


def refuse(ok: bool, reason: str) -> None:
    if not ok:
        raise SystemExit("REFUSE_P2_WAVE2C5: " + reason)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def file_at(root: Path, rel: str) -> Path:
    p = root / rel
    refuse(p.is_file() and not p.is_symlink(), "missing/unsafe protected file: " + rel)
    return p


def blob(root: Path, rel: str) -> str:
    return git(root, "hash-object", str(file_at(root, rel)))


def original_party_resource_names(root: Path) -> tuple[str, ...]:
    # HEAD refers to the pinned original upstream, never a private source.
    refuse(git(root, "rev-parse", "HEAD:" + OLD_STRINGS) == OLD_STRINGS_BLOB,
           "legacy XML frozen git blob drift")
    raw = subprocess.check_output(["git", "-C", str(root), "show", "HEAD:" + OLD_STRINGS])
    try:
        element = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SystemExit("REFUSE_P2_WAVE2C5: invalid frozen legacy XML") from exc
    refuse(element.tag == "resources" and not element.attrib, "invalid resource root")
    entries = list(element)
    refuse(len(entries) == 74, "frozen Party resource count drift")
    refuse(all(item.tag == "string" and set(item.attrib) == {"name"} for item in entries),
           "unexpected frozen resource entry")
    names = tuple(item.attrib["name"] for item in entries)
    refuse(len(set(names)) == 74 and all(re.fullmatch(r"party_[a-z0-9_]+", n) for n in names),
           "duplicate or unexpected frozen Party resource name")
    return names


def audit(root: Path) -> None:
    refuse(git(root, "rev-parse", "HEAD") == PINNED, "public upstream revision is not pinned")
    refuse(not git(root, "diff", "--cached", "--name-only"), "staged changes found")
    refuse(not git(root, "ls-files", "--others", "--exclude-standard"), "untracked files found")
    changed = set(git(root, "diff", "--name-only").splitlines())
    wanted = UPDATED | DELETED
    refuse(wanted <= changed, "cumulative Wave2C4d patch footprint incomplete")
    refuse(changed <= wanted | ALLOWED_GITLINKS, "unexpected changed path outside public wave scope")
    for rel in sorted(DELETED):
        refuse(not (root / rel).exists(), "obsolete native Party file remains: " + rel)
        refuse(git(root, "diff", "--name-status", "--", rel) == "D\t" + rel,
               "obsolete Party path has incorrect deletion status: " + rel)
    for rel in sorted(UPDATED):
        file_at(root, rel)
        refuse(git(root, "diff", "--name-status", "--", rel) == "M\t" + rel,
               "unexpected modified-file status: " + rel)

    refuse(blob(root, MANIFEST) == MANIFEST_BLOB, "Android manifest modified")
    manifest = file_at(root, MANIFEST).read_text(encoding="utf-8")
    for anchor in ('android:host="nuvio.tv"', 'android:pathPrefix="/party/"',
                   'android:scheme="https"'):
        refuse(anchor in manifest, "public invite Android App Link missing: " + anchor)
    refuse(blob(root, DEEP_LINK_TEST) == DEEP_LINK_TEST_BLOB,
           "frozen invite parser tests changed")
    deep = file_at(root, DEEP_LINK).read_text(encoding="utf-8")
    for anchor in (
        'private const val LEGACY_INVITE_CODE_LENGTH = 6',
        'private const val LEGACY_INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"',
        'private fun normalizeLegacyInviteCode(input: String): String',
        'private fun legacyInviteDeepLink(code: String?): AppDeepLink.Party?',
        'internal fun parseAppDeepLink(url: String): AppDeepLink?',
        '"party" -> legacyInviteDeepLink(',
    ):
        refuse(anchor in deep, "legacy invitation parser changed: " + anchor)
    refuse(deep.count("legacyInviteDeepLink(") == 3,
           "legacy invite parser callsites changed")
    refuse("com.nuvio.app.features.party" not in deep, "parser still imports deleted Party module")
    refuse("is AppDeepLink.Party ->" in file_at(root, MAIN).read_text(encoding="utf-8"),
           "invite consumption missing")
    refuse("currentNormalPlaybackPositionMs" in
           file_at(root, PLAYBACK).read_text(encoding="utf-8"),
           "normal playback position helper missing")
    refuse("PartyRoute" not in file_at(root, NAV).read_text(encoding="utf-8") +
           file_at(root, ROUTES).read_text(encoding="utf-8"),
           "deleted Party route remains in navigation")

    tracked = git(root, "ls-files").splitlines()
    refuse({p for p in tracked if p.startswith(PARTY_CORE) or p.startswith(PARTY_TEST)}
           == PARTY_FILES, "frozen Party file inventory drift")
    remaining_kotlin = [p for p in tracked if (p.endswith(".kt") or p.endswith(".java"))
                        and (root / p).is_file()]
    refuse(len(remaining_kotlin) == EXPECTED_KOTLIN_JAVA,
           f"remaining public Kotlin/Java count drift: {len(remaining_kotlin)}")
    for rel in remaining_kotlin:
        p = file_at(root, rel)
        body = p.read_text(encoding="utf-8")
        refuse("com.nuvio.app.features.party" not in body,
               "remaining Party Kotlin package dependency: " + rel)
        refuse(not OLD_PARTY_REFERENCES.search(body),
               "remaining legacy native Party Kotlin reference: " + rel)

    names = original_party_resource_names(root)
    exact = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(map(re.escape, names))
                       + r")(?![A-Za-z0-9_])")
    scanned, hit_paths = 0, []
    for rel in tracked:
        if rel == OLD_STRINGS or Path(rel).suffix.lower() not in SCANNABLE_SUFFIXES:
            continue
        p = root / rel
        if not p.exists():
            continue
        file_at(root, rel)
        refuse(p.stat().st_size <= 8_000_000, "oversized public source: " + rel)
        body = p.read_text(encoding="utf-8")
        scanned += 1
        if exact.search(body):
            hit_paths.append(rel)
        refuse(scanned <= 3500, "unexpectedly large public source inventory")
    refuse(scanned == EXPECTED_TEXT_SOURCE_RESOURCE_FILES,
           f"public source inventory drift: expected {EXPECTED_TEXT_SOURCE_RESOURCE_FILES}, got {scanned}")
    refuse(not hit_paths, "deleted Party strings still referenced: " + repr(hit_paths[:10]))
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    refuse(set(git(root, "diff", "--name-only").splitlines()) == changed,
           "read-only audit modified public source")

    print("P2_WAVE2C5_FINAL_PUBLIC_READ_ONLY_AUDIT=PASS")
    print(f"P2_WAVE2C5_APPROVED_KOTLIN_MODIFICATIONS={len(UPDATED)}")
    print(f"P2_WAVE2C5_APPROVED_LEGACY_DELETIONS={len(DELETED)}")
    print("P2_WAVE2C5_NATIVE_PARTY_CORE_REMOVED=12")
    print("P2_WAVE2C5_NATIVE_PARTY_TESTS_REMOVED=2")
    print("P2_WAVE2C5_OLD_PLAYER_BRIDGE_REMOVED=1")
    print("P2_WAVE2C5_OLD_PARTY_XML_REMOVED=1")
    print(f"P2_WAVE2C5_KOTLIN_JAVA_FILES_SCANNED={len(remaining_kotlin)}")
    print(f"P2_WAVE2C5_SOURCE_RESOURCE_FILES_SCANNED={scanned}")
    print(f"P2_WAVE2C5_DELETED_LEGACY_STRING_IDS={len(names)}")
    print("P2_WAVE2C5_ORPHAN_NATIVE_PARTY_REFERENCES=0")
    print("P2_WAVE2C5_DELETED_STRING_REFERENCES=0")
    print("P2_WAVE2C5_MANIFEST_INVITE_LINKS_PRESERVED=YES")
    print("P2_WAVE2C5_LEGACY_INVITE_PARSER_PRESERVED=YES")
    print("P2_WAVE2C5_EXISTING_INVITE_TESTS_UNCHANGED=YES")
    print("P2_WAVE2C5_NORMAL_PLAYBACK_PRESERVED=YES")
    print("P2_WAVE2C5_NO_PRIVATE_TOGETHER_CODE=YES")
    print("P2_WAVE2C5_PRIVATE_BUILD_NOT_TESTED=YES")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    audit(ap.parse_args().source.resolve(strict=True))


if __name__ == "__main__":
    main()
