#!/usr/bin/env python3
"""Stage17 P2 Wave2C4b - PUBLIC legacy Party invite-parser isolation.

Patch only AppUrlBridge.kt within a disposable checkout of the frozen PUBLIC
NuvioMedia/NuvioMobile upstream after approved waves through 2C3b and read-only
2C4a audit. Remove its two imports from native features/party, moving the exact
six-character invite normalizer into the local deep-link bridge. Leave ALL
public native Party core/tests, Android Manifest, invite handling, and private
Together sources untouched. Refuse unexpected upstream revisions or edits.
"""
import argparse
from pathlib import Path
import re
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
TEST_BASE = "composeApp/src/commonTest/kotlin/com/nuvio/app/"
DEEPLINK = BASE + "core/deeplink/AppUrlBridge.kt"
DEEPLINK_TEST = TEST_BASE + "core/deeplink/AppUrlBridgeTest.kt"
PARTY_REPO = BASE + "features/party/PartyRepository.kt"
PARTY_SCREEN = BASE + "features/party/PartyScreen.kt"
BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
MAIN = BASE + "MainAppContent.kt"
NAV = BASE + "AppNavigationSupport.kt"
ROUTES = BASE + "navigation/Routes.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"
STATE = BASE + "features/player/PlayerScreenRuntimeState.kt"
PARTY_DIR = BASE + "features/party/"
PARTY_TEST_DIR = TEST_BASE + "features/party/"

# All prior modified paths must already be present, but no other app sources may
# have changed before this step. The pinned baseline files below are unchanged
# by waves 1-2C3b (confirmed against frozen PUBLIC upstream Git blob SHAs).
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
    "navigation/Routes.kt",
)}
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
FROZEN_BLOBS = {
    DEEPLINK: "5f8e33f335361cc0329363e82d01ab98db998f03",
    DEEPLINK_TEST: "a1e48f97e9df99e3f44e490478c099ed367a9244",
    PARTY_REPO: "da7b20f459b6b68ef22ba196c629d383515761d5",
}
OLD_IMPORTS = (
    "import com.nuvio.app.features.party.PARTY_CODE_LENGTH\n",
    "import com.nuvio.app.features.party.normalizePartyCode\n",
)
OLD_PARSER = """private fun partyDeepLink(code: String?): AppDeepLink.Party? =
    code?.let(::normalizePartyCode)?.takeIf { it.length == PARTY_CODE_LENGTH }?.let(AppDeepLink::Party)
"""
NEW_PARSER = """// Isolated from the retired native Party feature. These frozen public rules
// must remain stable until the private Together invitation bridge is ported.
private const val LEGACY_INVITE_CODE_LENGTH = 6
private const val LEGACY_INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

private fun normalizeLegacyInviteCode(input: String): String =
    input.uppercase().filter { it in LEGACY_INVITE_CODE_ALPHABET }

private fun legacyInviteDeepLink(code: String?): AppDeepLink.Party? =
    code?.let(::normalizeLegacyInviteCode)
        ?.takeIf { it.length == LEGACY_INVITE_CODE_LENGTH }
        ?.let(AppDeepLink::Party)
"""
LEGACY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(condition: bool, why: str) -> None:
    if not condition:
        raise SystemExit("REFUSE_P2_WAVE2C4B: " + why)


def read(root: Path, path: str) -> str:
    p = root / path
    require(p.is_file() and not p.is_symlink(), "missing or unsafe public source: " + path)
    return p.read_text(encoding="utf-8")


def replace_one(text: str, old: str, new: str, label: str) -> str:
    require(text.count(old) == 1, "unexpected frozen parser anchor: " + label)
    return text.replace(old, new, 1)


def check_external_imports(root: Path, proposed: str) -> tuple[int, int]:
    paths = [path for path in git(root, "ls-files", "--", "*.kt").splitlines()
             if path.startswith("composeApp/src/") and (root / path).is_file()]
    require(len(paths) >= 1000, "unexpected Kotlin file count")
    external_imports = []
    old_party_symbols = re.compile(
        r"\b(?:PartyRepository|PartyRoute|PartyMedia|PartySync|PartyScreen|"
        r"PartyStream|PartySource|PartyEvent|PartyPanel|PartyPresence|"
        r"PARTY_CODE_LENGTH|normalizePartyCode|isValidPartyCode|"
        r"formatPartyCode|partyMediaKey|partyDeepLink|onOpenPartyMedia|"
        r"openPartyMedia|watchPartyTitle)\b"
    )
    symbols = []
    for rel in paths:
        if rel.startswith(PARTY_DIR) or rel.startswith(PARTY_TEST_DIR):
            continue
        content = proposed if rel == DEEPLINK else read(root, rel)
        for n, line in enumerate(content.splitlines(), 1):
            if "com.nuvio.app.features.party" in line:
                external_imports.append((rel, n))
            if old_party_symbols.search(line):
                symbols.append((rel, n))
    require(not external_imports, "native Party package still imported outside legacy core")
    require(not symbols, "legacy Party symbol still referenced outside legacy core")
    return (len(paths), len(external_imports))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    root = parser.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED, "wrong frozen PUBLIC upstream")
    require(not git(root, "diff", "--cached", "--name-only"), "staged files present")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(before), "cumulative 2C3b patches missing")
    require(before.issubset(PREVIOUS | ALLOWED_GITLINKS), "unapproved changes before wave")
    require(not (root / BRIDGE).exists(), "old Party player bridge remains")
    for p in (DEEPLINK, DEEPLINK_TEST, PARTY_REPO, PARTY_SCREEN, MAIN, NAV, ROUTES, PLAYBACK, STATE):
        read(root, p)
    for path, sha in FROZEN_BLOBS.items():
        require(git(root, "hash-object", str(root / path)) == sha,
                "frozen PUBLIC source unexpectedly changed: " + path)

    require("PartyRepository" not in read(root, MAIN), "2C3b orphan hook removal missing")
    require("PartyRoute" not in read(root, NAV) + read(root, ROUTES),
            "2C3a route removal missing")
    require("currentNormalPlaybackPositionMs" in read(root, PLAYBACK),
            "normal playback position helper missing")
    require("showPartyPanel" not in read(root, STATE), "legacy player state remains")
    require("is AppDeepLink.Party ->" in read(root, MAIN),
            "legacy invite consumption path missing")
    repo_text = read(root, PARTY_REPO)
    for anchor in (
        'fun normalizePartyCode(input: String): String =\n    input.uppercase().filter { it in PARTY_CODE_ALPHABET }',
        'const val PARTY_CODE_LENGTH = 6',
        'private const val PARTY_CODE_ALPHABET = "' + LEGACY_ALPHABET + '"',
    ):
        require(repo_text.count(anchor) == 1, "frozen legacy normalizer no longer matches")

    current = read(root, DEEPLINK)
    for item in OLD_IMPORTS:
        require(current.count(item) == 1, "missing/duplicate Party import")
    require(current.count(OLD_PARSER) == 1, "frozen deep-link parser changed")
    require(current.count("partyDeepLink(") == 3, "unexpected invite dispatch routes")
    test_source = read(root, DEEPLINK_TEST)
    for anchor in (
        'AppDeepLink.Party("K7M2QX"), parseAppDeepLink("nuvio://party/k7m-2qx")',
        'AppDeepLink.Party("K7M2QX"), parseAppDeepLink("https://nuvio.tv/party/K7M2QX")',
        'assertNull(parseAppDeepLink("https://evil.example/party/K7M2QX"))',
    ):
        require(anchor in test_source, "existing public invite regression test missing")

    updated = current
    for imp in OLD_IMPORTS:
        updated = replace_one(updated, imp, "", "import")
    updated = replace_one(updated, OLD_PARSER, NEW_PARSER, "normalizer")
    require(updated.count("partyDeepLink(") == 2, "unexpected dispatch changes")
    updated = updated.replace("partyDeepLink(", "legacyInviteDeepLink(")
    require(updated.count("legacyInviteDeepLink(") == 3,
            "legacy invite dispatch not fully retained")
    require("AppDeepLink.Party" in updated and "internal fun parseAppDeepLink" in updated,
            "invite parser removed")
    for sentinel in (
        'host == "nuvio.tv" && pathSegments.firstOrNull() == "party"',
        '"party" -> legacyInviteDeepLink(',
        '"downloads" -> AppDeepLink.Downloads',
        '"meta" -> {',
        'AppDeepLink::AddonInstall',
    ):
        require(sentinel in updated, "non-Party parser route unexpectedly modified")
    require("com.nuvio.app.features.party" not in updated,
            "deep-link parser still imports Party module")
    kt_scanned, external_count = check_external_imports(root, updated)

    (root / DEEPLINK).write_text(updated, encoding="utf-8")
    after = set(git(root, "diff", "--name-only").splitlines())
    require(after == before | {DEEPLINK}, "unexpected out-of-scope source changes")
    require(git(root, "hash-object", str(root / DEEPLINK_TEST)) == FROZEN_BLOBS[DEEPLINK_TEST],
            "existing invite tests unexpectedly modified")
    require(git(root, "hash-object", str(root / PARTY_REPO)) == FROZEN_BLOBS[PARTY_REPO],
            "native Party core unexpectedly modified")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2C4B_INVITE_PARSER_DETACHED=PASS")
    print("P2_WAVE2C4B_KOTLIN_FILES_TOUCHED=1")
    print(f"P2_WAVE2C4B_KOTLIN_FILES_SCANNED={kt_scanned}")
    print(f"P2_WAVE2C4B_EXTERNAL_PARTY_IMPORTS={external_count}")
    print("P2_WAVE2C4B_OLD_PARTY_SYMBOLS_OUTSIDE_CORE=0")
    print("P2_WAVE2C4B_INVITE_CODE_RULES_PRESERVED=YES")
    print("P2_WAVE2C4B_PUBLIC_INVITE_TESTS_UNCHANGED=YES")
    print("P2_WAVE2C4B_DEEPLINK_PARSER_AND_ANDROID_MANIFEST_PRESERVED=YES")
    print("P2_WAVE2C4B_NATIVE_PARTY_CORE_STILL_PRESENT=YES")
    print("P2_WAVE2C4B_NO_PRIVATE_TOGETHER_CODE=YES")


if __name__ == "__main__":
    main()
