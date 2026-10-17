#!/usr/bin/env python3
"""Stage17 P2 Wave2C2 — PUBLIC upstream player callback detachment only.

Requires frozen public upstream plus approved cumulative Waves 1, 2A, 2B1,
2B2, 2B3, 2C1a and 2C1b in a temporary runner checkout. The native Party
screen and navigation stay present, and the private Together repo is not read.
"""
import argparse
from pathlib import Path
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
MAIN = BASE + "MainAppContent.kt"
DEST = BASE + "PlayerDestination.kt"
SCREEN = BASE + "features/player/PlayerScreen.kt"
ARGS = BASE + "features/player/PlayerScreenArgs.kt"
BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
STATE = BASE + "features/player/PlayerScreenRuntimeState.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"

# Blob hashes of three files not modified by any previous wave.
FROZEN_BLOBS = {
    DEST: "6b5c676a4012d66738adef824c0e417698155d4e",
    SCREEN: "9160de7c07544cdc5e4fab60c11fa5b33f03a41c",
    ARGS: "81581c8af3c3676aa104c80f5a6b6e152a04daaa",
}
PREVIOUS = {BASE + name for name in (
    "SettingsDestinations.kt", "AppShellComponents.kt", "MainAppContent.kt",
    "features/settings/SettingsScreen.kt", "features/settings/SettingsRootPage.kt",
    "StreamDestination.kt", "features/player/PlayerScreenRuntimeUi.kt",
    "features/player/PlayerScreenRuntimeGestureActions.kt",
    "features/player/PlayerScreenRuntimeEffects.kt", "features/player/PlayerControls.kt",
    "features/player/PlayerControlActions.kt",
    "features/player/PlayerScreenRuntimePlaybackActions.kt",
    "features/player/PlayerScreenRuntimeState.kt",
    "features/player/PlayerScreenRuntimeParty.kt",
)}
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
CALLBACK_NAME = "onOpenPartyMedia"
PARTY_IMPORT = "import com.nuvio.app.features.party.PartyMedia\n"
# Exact removal targets: each occurrence must exist once in its file.
REMOVALS = {
    MAIN: (
        "                        onOpenPartyMedia = ::openPartyMedia,\n",
    ),
    DEST: (
        PARTY_IMPORT,
        "    onOpenPartyMedia: (PartyMedia) -> Unit,\n",
        "        onOpenPartyMedia = onOpenPartyMedia,\n",
    ),
    SCREEN: (
        PARTY_IMPORT,
        "    onOpenPartyMedia: (PartyMedia) -> Unit = {},\n",
        "            onOpenPartyMedia = onOpenPartyMedia,\n",
    ),
    ARGS: (
        PARTY_IMPORT,
        "    val onOpenPartyMedia: (PartyMedia) -> Unit = {},\n",
    ),
}
NORMAL_GATES = {
    MAIN: ("PlayerDestination(", "entry<PartyRoute>", "fun openPartyMedia(media: PartyMedia)"),
    DEST: ("PlayerScreen(", "onOpenExternalUrl = { url ->", "openExternalStreamUrl(url)"),
    SCREEN: ("PlayerScreenContent(", "PlayerScreenArgs(", "onOpenExternalUrl = onOpenExternalUrl"),
    ARGS: ("internal data class PlayerScreenArgs(", "val onBack: () -> Unit", "val parentMetaId: String"),
}

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit("REFUSE_P2_WAVE2C2: " + reason)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED, "unexpected public upstream commit")
    require(not git(root, "diff", "--cached", "--name-only"), "staged changes")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(before), "approved waves not all applied")
    require(before.issubset(PREVIOUS | ALLOWED_GITLINKS), "unrelated modified paths")
    require(not (root / BRIDGE).exists(), "Wave2C1b legacy bridge not removed")
    for rel in (MAIN, DEST, SCREEN, ARGS, STATE, PLAYBACK):
        require((root / rel).is_file() and not (root / rel).is_symlink(),
                "missing/unsafe public source: " + rel)
    for rel, sha in FROZEN_BLOBS.items():
        require(git(root, "hash-object", str(root / rel)) == sha,
                "unexpected upstream source hash for " + rel)
    st = (root / STATE).read_text(encoding="utf-8")
    require("var showPartyPanel " not in st and "var partyRateNudge" not in st,
            "Wave2C1b state cleanup not present")
    playback = (root / PLAYBACK).read_text(encoding="utf-8")
    require(playback.count("fun PlayerScreenRuntime.currentNormalPlaybackPositionMs(): Long") == 1,
            "Wave2C1a normal player timing helper missing")

    pending = {}
    for rel, needles in REMOVALS.items():
        src = (root / rel).read_text(encoding="utf-8")
        require(src.count(CALLBACK_NAME) == sum(s.count(CALLBACK_NAME) for s in needles),
                "unexpected Party callback count in " + rel)
        for needle in needles:
            require(src.count(needle) == 1,
                    "required unique source anchor missing for " + rel + ": " + repr(needle))
        after = src
        for needle in needles:
            after = after.replace(needle, "", 1)
        require(CALLBACK_NAME not in after, "old callback still referenced in " + rel)
        for sentinel in NORMAL_GATES[rel]:
            require(sentinel in after, "required normal/legacy navigation code absent: " + sentinel)
        # Party itself is still navigable on this wave; do not remove this function.
        if rel == MAIN:
            require("onWatch = ::openPartyMedia" in after,
                    "native Party screen callback must remain until navigation wave")
        pending[rel] = after

    # All guards are checked before the first file is written.
    for rel, after in pending.items():
        (root / rel).write_text(after, encoding="utf-8")
    changed = set(git(root, "diff", "--name-only").splitlines())
    expected = before | set(REMOVALS)
    require(changed == expected, "out-of-scope modifications: " + repr(sorted(changed ^ expected)))
    require(not (root / BRIDGE).exists(), "removed Party bridge reappeared")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2C2_PLAYER_CALLBACKS_DETACHED=PASS")
    print("P2_WAVE2C2_PUBLIC_KOTLIN_FILES_TOUCHED=4")
    print("P2_WAVE2C2_PARTY_ROUTE_AND_SCREEN_PRESERVED=YES")
    print("P2_WAVE2C2_NORMAL_PLAYBACK_HELPER_PRESERVED=YES")
    print("P2_WAVE2C2_NO_PRIVATE_TOGETHER_CODE=YES")

if __name__ == "__main__":
    main()
