#!/usr/bin/env python3
"""Stage17 P2 Wave2C4d: remove ONLY frozen PUBLIC obsolete Party strings XML.

Requires exact pinned PUBLIC NuvioMedia/NuvioMobile checkout, cumulatively
patched through Wave2C4c. Does not touch manifest, invite parser, normal player,
private Together code, GitHub repo, or published artifacts. Fail closed on drift.
"""
import argparse
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
TEST_BASE = "composeApp/src/commonTest/kotlin/com/nuvio/app/"
PARTY_DIR = BASE + "features/party/"
PARTY_TEST_DIR = TEST_BASE + "features/party/"
DEEPLINK = BASE + "core/deeplink/AppUrlBridge.kt"
DEEPLINK_TEST = TEST_BASE + "core/deeplink/AppUrlBridgeTest.kt"
MAIN = BASE + "MainAppContent.kt"
NAV = BASE + "AppNavigationSupport.kt"
ROUTES = BASE + "navigation/Routes.kt"
OLD_PLAYER_BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"
MANIFEST = "androidApp/src/main/AndroidManifest.xml"
STRINGS = "composeApp/src/commonMain/composeResources/values/strings_party.xml"

FROZEN_STRINGS_SHA = "426af4690a4425f02f75f81674998a8b498421a0"
FROZEN_MANIFEST_SHA = "a73b22ab63c98e6e8f552c1adec791086eca28d2"
FROZEN_DEEPLINK_TEST_SHA = "a1e48f97e9df99e3f44e490478c099ed367a9244"
EXPECTED_LEGACY_STRINGS = 74
EXPECTED_OUTSIDE_PARTY_KOTLIN_JAVA = 1247

PREVIOUS = {BASE + p for p in (
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
    "navigation/Routes.kt", "core/deeplink/AppUrlBridge.kt",
)}
OLD_CORE_NAMES = (
    "PartyApi.kt", "PartyChannel.kt", "PartyClock.kt", "PartyCode.kt",
    "PartyDetails.kt", "PartyModels.kt", "PartyPanel.kt", "PartyRepository.kt",
    "PartyScreen.kt", "PartySourceMatch.kt", "PartySync.kt", "PartyUi.kt",
)
OLD_TEST_NAMES = ("PartyStreamTest.kt", "PartySyncTest.kt")
OLD_PARTY_PATHS = ({PARTY_DIR + name for name in OLD_CORE_NAMES}
                   | {PARTY_TEST_DIR + name for name in OLD_TEST_NAMES})
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
SCANNABLE_SUFFIXES = {
    ".kt", ".java", ".xml", ".swift", ".plist", ".kts",
    ".gradle", ".properties", ".toml", ".json", ".js", ".ts", ".tsx",
}


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit("REFUSE_P2_WAVE2C4D: " + message)


def file_at(root: Path, rel: str) -> Path:
    p = root / rel
    require(p.is_file() and not p.is_symlink(), "missing/unsafe file: " + rel)
    return p


def blob(root: Path, rel: str) -> str:
    return git(root, "hash-object", str(file_at(root, rel)))


def parse_legacy_resources(root: Path) -> tuple[str, ...]:
    require(blob(root, STRINGS) == FROZEN_STRINGS_SHA, "frozen legacy strings XML changed")
    data = file_at(root, STRINGS).read_bytes()
    try:
        element = ET.fromstring(data)
    except ET.ParseError as exc:
        raise SystemExit("REFUSE_P2_WAVE2C4D: invalid legacy strings XML") from exc
    require(element.tag == "resources" and not element.attrib,
            "unexpected legacy XML root")
    children = list(element)
    require(len(children) == EXPECTED_LEGACY_STRINGS,
            f"unexpected legacy string count: {len(children)}")
    require(all(child.tag == "string" and set(child.attrib) == {"name"}
                for child in children), "non-string entry in legacy XML")
    names = tuple(child.attrib["name"] for child in children)
    require(len(set(names)) == len(names), "duplicate legacy resource name")
    require(all(re.fullmatch(r"party_[a-z0-9_]+", name) for name in names),
            "unrelated string in legacy resources")
    require("party_title" in names and "party_share_description" in names,
            "legacy resource sentinel missing")
    return names


def verify_no_external_references(root: Path, names: tuple[str, ...]) -> tuple[int, int]:
    # Search every relevant tracked source/resources file AFTER cumulative core removal.
    # A match is fatal; no XML gets deleted on an unexpected dependency.
    exact = re.compile(r"(?<![A-Za-z0-9_])(?:" + "|".join(re.escape(n) for n in names)
                       + r")(?![A-Za-z0-9_])")
    checked, hits = 0, []
    for rel in git(root, "ls-files").splitlines():
        if rel == STRINGS or Path(rel).suffix.lower() not in SCANNABLE_SUFFIXES:
            continue
        path = root / rel
        if not path.exists():
            continue  # Old Party .kt and its tests were removed by Wave2C4c.
        require(path.is_file() and not path.is_symlink(), "unsafe tracked source: " + rel)
        require(path.stat().st_size <= 8_000_000, "oversized text source: " + rel)
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            raise SystemExit("REFUSE_P2_WAVE2C4D: source encoding error: " + rel) from exc
        checked += 1
        matched = set(exact.findall(body))
        if matched:
            hits.append((rel, ",".join(sorted(matched)[:8])))
        require(checked <= 3500, "unexpectedly large source inventory")
    require(checked >= 1250, "unexpectedly small source inventory")
    require(not hits, "still-used native Party resource(s): " + repr(hits[:10]))
    return checked, len(hits)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED, "wrong pinned PUBLIC upstream")
    require(not git(root, "diff", "--cached", "--name-only"), "staged changes found")
    require(not git(root, "ls-files", "--others", "--exclude-standard"),
            "untracked files found before wave")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS | OLD_PARTY_PATHS <= before, "prior waves through 2C4c missing")
    require(before <= PREVIOUS | OLD_PARTY_PATHS | ALLOWED_GITLINKS,
            "unexpected preexisting modified public file")
    tracked = set(git(root, "ls-files").splitlines())
    require(STRINGS in tracked, "legacy XML not tracked")
    require({p for p in tracked if p.startswith(PARTY_DIR) or p.startswith(PARTY_TEST_DIR)}
            == OLD_PARTY_PATHS, "Party source inventory drift")
    for rel in OLD_PARTY_PATHS | {OLD_PLAYER_BRIDGE}:
        require(not (root / rel).exists(), "old Party Kotlin file still exists: " + rel)
        require(git(root, "diff", "--name-status", "--", rel) == "D\t" + rel,
                "old Party file not marked deleted: " + rel)
    kotlin_java = [rel for rel in tracked if (rel.endswith(".kt") or rel.endswith(".java"))
                   and (root / rel).is_file()]
    require(len(kotlin_java) == EXPECTED_OUTSIDE_PARTY_KOTLIN_JAVA,
            f"unexpected Kotlin/Java inventory: {len(kotlin_java)}")

    manifest_hash = blob(root, MANIFEST)
    require(manifest_hash == FROZEN_MANIFEST_SHA, "Android manifest changed")
    manifest = file_at(root, MANIFEST).read_text(encoding="utf-8")
    for anchor in ('android:host="nuvio.tv"', 'android:pathPrefix="/party/"',
                   'android:scheme="https"'):
        require(anchor in manifest, "Party invite intent filter missing: " + anchor)
    require(blob(root, DEEPLINK_TEST) == FROZEN_DEEPLINK_TEST_SHA,
            "existing invite tests modified")
    deep_hash = blob(root, DEEPLINK)
    deep = file_at(root, DEEPLINK).read_text(encoding="utf-8")
    for anchor in (
        'private const val LEGACY_INVITE_CODE_LENGTH = 6',
        'private const val LEGACY_INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"',
        'private fun normalizeLegacyInviteCode(input: String): String',
        'private fun legacyInviteDeepLink(code: String?): AppDeepLink.Party?',
        'internal fun parseAppDeepLink(url: String): AppDeepLink?',
        '"party" -> legacyInviteDeepLink(',
    ):
        require(anchor in deep, "isolated legacy invite parser missing: " + anchor)
    require(deep.count("legacyInviteDeepLink(") == 3, "invite dispatch count drift")
    require("is AppDeepLink.Party ->" in file_at(root, MAIN).read_text(encoding="utf-8"),
            "MainApp Party invite consume branch missing")
    require("currentNormalPlaybackPositionMs" in
            file_at(root, PLAYBACK).read_text(encoding="utf-8"),
            "normal playback helper missing")
    require("PartyRoute" not in (file_at(root, NAV).read_text(encoding="utf-8") +
                                 file_at(root, ROUTES).read_text(encoding="utf-8")),
            "old Party route remains")

    legacy_names = parse_legacy_resources(root)
    source_count, reference_count = verify_no_external_references(root, legacy_names)
    file_at(root, STRINGS).unlink()
    require(not (root / STRINGS).exists(), "obsolete strings file not deleted")
    require(set(git(root, "diff", "--name-only").splitlines()) == before | {STRINGS},
            "unexpected source edits during resource removal")
    require(git(root, "diff", "--name-status", "--", STRINGS) == "D\t" + STRINGS,
            "resource XML was not a clean tracked deletion")
    require(blob(root, MANIFEST) == manifest_hash and blob(root, DEEPLINK) == deep_hash,
            "protected invite file changed")
    require(blob(root, DEEPLINK_TEST) == FROZEN_DEEPLINK_TEST_SHA,
            "protected invite test changed")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2C4D_LEGACY_PARTY_STRINGS_REMOVAL=PASS")
    print("P2_WAVE2C4D_RESOURCE_XML_FILES_DELETED=1")
    print(f"P2_WAVE2C4D_LEGACY_PARTY_STRING_IDS_DELETED={len(legacy_names)}")
    print(f"P2_WAVE2C4D_OTHER_PUBLIC_SOURCE_RESOURCE_FILES_SCANNED={source_count}")
    print(f"P2_WAVE2C4D_REMAINING_REFERENCES_TO_DELETED_STRINGS={reference_count}")
    print("P2_WAVE2C4D_ANDROID_MANIFEST_PARTY_LINKS_RETAINED=YES")
    print("P2_WAVE2C4D_INVITE_PARSER_AND_TESTS_RETAINED=YES")
    print("P2_WAVE2C4D_NORMAL_PLAYBACK_RETAINED=YES")
    print("P2_WAVE2C4D_NATIVE_PARTY_KOTLIN_ALREADY_REMOVED=YES")
    print("P2_WAVE2C4D_NO_PRIVATE_TOGETHER_CODE=YES")

if __name__ == "__main__":
    main()
