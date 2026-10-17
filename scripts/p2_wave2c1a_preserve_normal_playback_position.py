#!/usr/bin/env python3
"""Stage17 P2 Wave2C1a: PUBLIC upstream normal-playback helper isolation.

Requires approved cumulative public-only Waves 1 / 2A / 2B1 / 2B2 / 2B3.
Touches only two already-modified Kotlin files in an ephemeral upstream checkout.
DOES NOT delete or change the native Party bridge or its six state fields.
DOES NOT touch private Nuvio Together code.
"""

import argparse
from pathlib import Path
import subprocess

PINNED_UPSTREAM = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
PLAYER = BASE + "features/player/"
PARTY_BRIDGE = PLAYER + "PlayerScreenRuntimeParty.kt"
GESTURES = PLAYER + "PlayerScreenRuntimeGestureActions.kt"
PLAYBACK = PLAYER + "PlayerScreenRuntimePlaybackActions.kt"
PARTY_BRIDGE_SHA = "a7226df096c0ba7c66e0e89c7acd7f183d9ad59f"

# Exact modified files left by the five already-approved cumulative waves.
REQUIRED_PREVIOUS = {BASE + file for file in (
    "SettingsDestinations.kt",
    "AppShellComponents.kt",
    "MainAppContent.kt",
    "features/settings/SettingsScreen.kt",
    "features/settings/SettingsRootPage.kt",
    "StreamDestination.kt",
    "features/player/PlayerScreenRuntimeUi.kt",
    "features/player/PlayerScreenRuntimeGestureActions.kt",
    "features/player/PlayerScreenRuntimeEffects.kt",
    "features/player/PlayerControls.kt",
    "features/player/PlayerControlActions.kt",
    "features/player/PlayerScreenRuntimePlaybackActions.kt",
)}
# Uninitialized upstream submodule gitlinks may appear in git diff.
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}

# Body copied VERBATIM from the pinned PUBLIC Nuvio source.
ORIGINAL_HELPER = """internal fun PlayerScreenRuntime.currentPlaybackPositionMs(): Long {
    val snapshot = playbackSnapshot
    if (!snapshot.isPlaying || snapshot.isLoading) return snapshot.positionMs
    val elapsedMs = playbackSnapshotMark?.elapsedNow()?.inWholeMilliseconds?.coerceIn(0L, 1_000L) ?: 0L
    return snapshot.positionMs + (elapsedMs * snapshot.playbackSpeed).toLong()
}
"""
NORMAL_HELPER = ORIGINAL_HELPER.replace(
    "fun PlayerScreenRuntime.currentPlaybackPositionMs():",
    "fun PlayerScreenRuntime.currentNormalPlaybackPositionMs():",
)
GESTURE_OLD_CALL = "        ?: currentPlaybackPositionMs()\n"
GESTURE_NEW_CALL = "        ?: currentNormalPlaybackPositionMs()\n"
INSERT_BEFORE = "internal val PlayerScreenRuntime.activePlaybackIdentity: String"


def git(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True
    ).strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("REFUSE_P2_WAVE2C1A: " + message)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, type=Path,
                    help="Path to temporary checkout of pinned PUBLIC upstream")
    root = ap.parse_args().source.resolve(strict=True)

    require(git(root, "rev-parse", "HEAD") == PINNED_UPSTREAM,
            "wrong upstream SHA")
    require(not git(root, "diff", "--cached", "--name-only"),
            "unexpected staged changes")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(REQUIRED_PREVIOUS.issubset(before), "previous 5 waves not applied")
    require(before.issubset(REQUIRED_PREVIOUS | ALLOWED_GITLINKS),
            "unexpected pre-existing changed files")

    party = root / PARTY_BRIDGE
    gestures = root / GESTURES
    playback = root / PLAYBACK
    for file in (party, gestures, playback):
        require(file.is_file() and not file.is_symlink(),
                "missing/unsafe upstream input: " + str(file))

    require(git(root, "hash-object", str(party)) == PARTY_BRIDGE_SHA,
            "Party bridge does not match pinned upstream")
    original_party = party.read_text(encoding="utf-8")
    original_gestures = gestures.read_text(encoding="utf-8")
    original_playback = playback.read_text(encoding="utf-8")

    require(original_party.count(ORIGINAL_HELPER) == 1,
            "source position-helper body differs")
    require(original_gestures.count(GESTURE_OLD_CALL) == 1,
            "normal gesture call not unique")
    require(original_gestures.count("currentPlaybackPositionMs()") == 1,
            "normal gesture still has other legacy-helper calls")
    for legacy in ("isPartyControlLocked", "publishPartyPlayback", "partyBlocksControl"):
        require(legacy not in original_gestures,
                "Wave2B1 gestures patch missing: " + legacy)
    require(original_playback.count(INSERT_BEFORE) == 1,
            "normal playback helper insertion anchor not unique")
    require("    val reported = snapshot\n" in original_playback,
            "Wave2B3 snapshot patch not present")
    require("partyRateNudge" not in original_playback,
            "legacy Party rate logic remains")
    require("currentNormalPlaybackPositionMs" not in
            (original_gestures + original_playback + original_party),
            "new normal helper already exists")

    next_gestures = original_gestures.replace(
        GESTURE_OLD_CALL, GESTURE_NEW_CALL, 1)
    next_playback = original_playback.replace(
        INSERT_BEFORE, NORMAL_HELPER + "\n" + INSERT_BEFORE, 1)

    require(next_playback.count(NORMAL_HELPER) == 1,
            "helper not copied exactly once")
    require(next_gestures.count(GESTURE_NEW_CALL) == 1,
            "normal gesture was not redirected once")
    require(NORMAL_HELPER.replace("currentNormalPlaybackPositionMs()",
                                  "currentPlaybackPositionMs()") == ORIGINAL_HELPER,
            "helper arithmetic changed")
    for required in ("playerController?.pause()", "playerController?.play()",
                     "playerController?.seekBy(offsetMs)",
                     "scheduleProgressSyncAfterSeek()", "handleDoubleTapSeek("):
        require(required in next_gestures,
                "normal gestures missing: " + required)
    for required in ("updatePlaybackSnapshot(",
                     "reported.copy(durationMs = playbackSnapshot.durationMs)",
                     "activePlaybackIdentity: String"):
        require(required in next_playback,
                "normal playback state missing: " + required)

    # Only two PUBLIC Kotlin source files are updated, in the runner clone.
    gestures.write_text(next_gestures, encoding="utf-8")
    playback.write_text(next_playback, encoding="utf-8")
    after = set(git(root, "diff", "--name-only").splitlines())
    require(after == before, "unexpected touched paths")
    require(git(root, "hash-object", str(party)) == PARTY_BRIDGE_SHA,
            "Party bridge was modified")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])

    print("P2_WAVE2C1A_HELPER_TRANSFER=PASS")
    print("P2_WAVE2C1A_NORMAL_GESTURE_REDIRECT=PASS")
    print("P2_WAVE2C1A_BRIDGE_UNCHANGED=YES")
    print("P2_WAVE2C1A_NO_FILES_DELETED=YES")
    print("NO_PRIVATE_TOGETHER_CODE=YES")


if __name__ == "__main__":
    main()
