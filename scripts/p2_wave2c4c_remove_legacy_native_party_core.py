#!/usr/bin/env python3
"""Stage17 P2 Wave2C4c: delete ONLY frozen PUBLIC native Watch Party Kotlin core/tests.

Run only in a disposable checkout of pinned PUBLIC NuvioMedia/NuvioMobile after
all approved patches through Wave2C4b. Do not publish the checkout or APK.
Keep deep-link parsing/tests, AndroidManifest.xml, and strings_party.xml intact.
Refuse revision drift, extra files, altered legacy source blobs or external uses.
Private Together / Stage16 sources are never read by this script.
"""
import argparse
from pathlib import Path
import re
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
TEST_BASE = "composeApp/src/commonTest/kotlin/com/nuvio/app/"
PARTY_DIR = BASE + "features/party/"
PARTY_TEST_DIR = TEST_BASE + "features/party/"
CORE_BLOBS = {
    "PartyApi.kt": "12c2a41438fc50ec85ecaa632f8460f0201eddbe",
    "PartyChannel.kt": "093cd3caf6594dd7e59bafac769cd80e9de12989",
    "PartyClock.kt": "13bff36b0add2d1c6a27bdb99006d98e7be67d14",
    "PartyCode.kt": "174694c6c4e69baa24b6add8e47dd0f8abfdfe76",
    "PartyDetails.kt": "c34fccc1d7391a4465bb1353b05fe63fc0a913d1",
    "PartyModels.kt": "44cb5a4a6f8601519dfeb25e426a903e875752a6",
    "PartyPanel.kt": "adca6ae752963c509baaa8e0e21545654817329e",
    "PartyRepository.kt": "da7b20f459b6b68ef22ba196c629d383515761d5",
    "PartyScreen.kt": "45ca5f324b7ae87cf8407bb7a5f843a8f2cda709",
    "PartySourceMatch.kt": "11024698421f77a4da3bfcbf13d4e86574de5de4",
    "PartySync.kt": "4810c985fb7080963633decaf34cf32e90aed889",
    "PartyUi.kt": "f614d1f9353495bad62bce14ec8d40a39d82df52",
}
TEST_BLOBS = {
    "PartyStreamTest.kt": "91d53bcadc59926e5a72db92a8fbafa5ae807322",
    "PartySyncTest.kt": "f21803d7af224ee7d7e9eae3e1633abd48ea8f43",
}
DEEPLINK = BASE + "core/deeplink/AppUrlBridge.kt"
DEEPLINK_TEST = TEST_BASE + "core/deeplink/AppUrlBridgeTest.kt"
MAIN = BASE + "MainAppContent.kt"
NAV = BASE + "AppNavigationSupport.kt"
ROUTES = BASE + "navigation/Routes.kt"
STATE = BASE + "features/player/PlayerScreenRuntimeState.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"
OLD_BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
MANIFEST = "androidApp/src/main/AndroidManifest.xml"
STRINGS = "composeApp/src/commonMain/composeResources/values/strings_party.xml"
UNTOUCHED_BLOBS = {
    DEEPLINK_TEST: "a1e48f97e9df99e3f44e490478c099ed367a9244",
    MANIFEST: "a73b22ab63c98e6e8f552c1adec791086eca28d2",
    STRINGS: "426af4690a4425f02f75f81674998a8b498421a0",
}
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
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
EXPECTED_EXTERNAL_KOTLIN_JAVA_FILES = 1247  # 1262 pinned files - 1 old bridge - 14 native Party files
LEGACY_SYMBOLS = re.compile(
    r"\b(?:PartyRepository|PartyRoute|PartyMedia|PartySync|PartyScreen|"
    r"PartyStream|PartySource|PartyEvent|PartyPanel|PartyPresence|"
    r"PARTY_CODE_LENGTH|normalizePartyCode|isValidPartyCode|formatPartyCode|"
    r"partyMediaKey|partyDeepLink|onOpenPartyMedia|openPartyMedia|watchPartyTitle)\b"
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit("REFUSE_P2_WAVE2C4C: " + reason)


def checked_file(root: Path, rel: str) -> Path:
    p = root / rel
    require(p.is_file() and not p.is_symlink(), "missing/unsafe public file: " + rel)
    return p


def git_hash(root: Path, rel: str) -> str:
    return git(root, "hash-object", str(checked_file(root, rel)))


def scan_external_sources(root: Path, excluded: set[str]) -> int:
    # Every tracked Kotlin/Java file in the public checkout, not just ComposeApp.
    sources = [p for p in git(root, "ls-files", "--", "*.kt", "*.java").splitlines()
               if p not in excluded and (root / p).is_file()]
    require(len(sources) == EXPECTED_EXTERNAL_KOTLIN_JAVA_FILES,
            f"pinned public Kotlin/Java inventory drift: expected {EXPECTED_EXTERNAL_KOTLIN_JAVA_FILES}, found {len(sources)}")
    for rel in sources:
        p = checked_file(root, rel)
        body = p.read_text(encoding="utf-8")
        require("com.nuvio.app.features.party" not in body,
                "external native Party package use: " + rel)
        require(not LEGACY_SYMBOLS.search(body),
                "external old native Party symbol use: " + rel)
    return len(sources)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    root = ap.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED, "upstream SHA not pinned")
    require(not git(root, "diff", "--cached", "--name-only"), "staged files found")
    require(not git(root, "ls-files", "--others", "--exclude-standard"), "untracked files found")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(before), "waves through Wave2C4b not applied")
    require(before.issubset(PREVIOUS | ALLOWED_GITLINKS), "unexpected prior file modification")
    require(not (root / OLD_BRIDGE).exists(), "old player Party bridge remains")
    require("PartyRoute" not in checked_file(root, NAV).read_text(encoding="utf-8") +
            checked_file(root, ROUTES).read_text(encoding="utf-8"),
            "old Party route remains")
    require("PartyRepository" not in checked_file(root, MAIN).read_text(encoding="utf-8"),
            "old Party app event collector remains")
    require("is AppDeepLink.Party ->" in checked_file(root, MAIN).read_text(encoding="utf-8"),
            "invite consumption branch missing")
    require("showPartyPanel" not in checked_file(root, STATE).read_text(encoding="utf-8"),
            "old Party player state remains")
    require("currentNormalPlaybackPositionMs" in
            checked_file(root, PLAYBACK).read_text(encoding="utf-8"),
            "normal playback position helper missing")

    preserved = {DEEPLINK: git_hash(root, DEEPLINK)}
    for path, expected_sha in UNTOUCHED_BLOBS.items():
        require(git_hash(root, path) == expected_sha, "untouched public file drift: " + path)
        preserved[path] = expected_sha
    deep = checked_file(root, DEEPLINK).read_text(encoding="utf-8")
    for anchor in (
        'private const val LEGACY_INVITE_CODE_LENGTH = 6',
        'private const val LEGACY_INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"',
        'private fun normalizeLegacyInviteCode(input: String): String',
        'private fun legacyInviteDeepLink(code: String?): AppDeepLink.Party?',
        'internal fun parseAppDeepLink(url: String): AppDeepLink?',
        'host == "nuvio.tv" && pathSegments.firstOrNull() == "party"',
        '"party" -> legacyInviteDeepLink(',
    ):
        require(anchor in deep, "Wave2C4b invite parser missing anchor: " + anchor)
    require(deep.count("legacyInviteDeepLink(") == 3, "legacy invite routes changed")

    deletion = {PARTY_DIR + name: sha for name, sha in CORE_BLOBS.items()}
    deletion.update({PARTY_TEST_DIR + name: sha for name, sha in TEST_BLOBS.items()})
    tracked = set(git(root, "ls-files").splitlines())
    existing_party_paths = {p for p in tracked if p.startswith(PARTY_DIR) or p.startswith(PARTY_TEST_DIR)}
    require(existing_party_paths == set(deletion), "unexpected Party module files in frozen tree")
    for rel, sha in deletion.items():
        require(git_hash(root, rel) == sha, "frozen public Party source changed: " + rel)
    scanned = scan_external_sources(root, set(deletion))
    for rel in deletion:
        (root / rel).unlink()
    for rel in deletion:
        require(not (root / rel).exists(), "deletion failed: " + rel)
    require(set(git(root, "diff", "--name-only").splitlines()) == before | set(deletion),
            "changes outside approved cumulative paths")
    for rel in deletion:
        require(git(root, "diff", "--name-status", "--", rel) == "D\t" + rel,
                "unexpected git change status: " + rel)
    require(not list((root / PARTY_DIR).glob("*.kt")) and
            not list((root / PARTY_TEST_DIR).glob("*.kt")),
            "native Party Kotlin files remain")
    for rel, sha in preserved.items():
        require(git_hash(root, rel) == sha, "protected public file changed: " + rel)
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2C4C_INVENTORY_GUARD_CORRECTED=PASS")
    print("P2_WAVE2C4C_NATIVE_PARTY_REMOVAL=PASS")
    print(f"P2_WAVE2C4C_NATIVE_PARTY_KOTLIN_FILES_DELETED={len(CORE_BLOBS)}")
    print(f"P2_WAVE2C4C_NATIVE_PARTY_TEST_FILES_DELETED={len(TEST_BLOBS)}")
    print(f"P2_WAVE2C4C_OTHER_KOTLIN_JAVA_FILES_SCANNED={scanned}")
    print("P2_WAVE2C4C_EXTERNAL_NATIVE_PARTY_REFERENCES=0")
    print("P2_WAVE2C4C_INVITE_PARSER_AND_TESTS_PRESERVED=YES")
    print("P2_WAVE2C4C_NORMAL_PLAYBACK_PATH_PRESERVED=YES")
    print("P2_WAVE2C4C_ANDROID_MANIFEST_PRESERVED=YES")
    print("P2_WAVE2C4C_STRINGS_PARTY_XML_RETAINED=YES")
    print("P2_WAVE2C4C_NO_PRIVATE_TOGETHER_CODE=YES")


if __name__ == "__main__":
    main()
