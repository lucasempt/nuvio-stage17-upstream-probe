#!/usr/bin/env python3
"""Stage17 P2 Wave2B1, isolated PUBLIC Nuvio: remove native Party hooks in
player gesture actions while retaining normal play/pause, seek, volume and speed.
NOT full Watch Party removal; NO private Together code.
"""
import argparse
from pathlib import Path
import subprocess

SHA = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
REL = BASE + "features/player/PlayerScreenRuntimeGestureActions.kt"
EXPECTED_BLOB = "9ca6dccdfc4e968b80fa0a4a6f0f29f19feea365"
WAVE1 = {BASE + x for x in (
    "SettingsDestinations.kt", "AppShellComponents.kt", "MainAppContent.kt",
    "features/settings/SettingsScreen.kt", "features/settings/SettingsRootPage.kt",
)}
WAVE2A = {BASE + x for x in (
    "StreamDestination.kt", "features/player/PlayerScreenRuntimeUi.kt",
)}
GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}

# Order is intentional: more-indented target first to avoid substring collisions.
EDITS = (
    ("    if (isPartyControlLocked) {\n        toggleOwnPlayback()\n        return\n    }\n", ""),
    ("    publishPartyPlayback(positionMs = if (playbackSnapshot.isEnded) 0L else currentPlaybackPositionMs())\n", ""),
    ("    val targetMs = if (isPartyControlLocked) ownSeekTarget(requestedMs) ?: return else requestedMs\n",
     "    val targetMs = requestedMs\n"),
    ("    if (isPartySynced) playerController?.seekTo(targetMs) else playerController?.seekBy(offsetMs)\n",
     "    playerController?.seekBy(offsetMs)\n"),
    ("    publishPartyPlayback(positionMs = targetMs)\n", ""),
    ("    val targetPositionMs = if (isPartyControlLocked) ownSeekTarget(requestedPositionMs) ?: return else requestedPositionMs\n",
     "    val targetPositionMs = requestedPositionMs\n"),
    ("            publishPartyPlayback(positionMs = targetPositionMs)\n", ""),
    ("    publishPartyPlayback(positionMs = targetPositionMs)\n", ""),
    ("    if (partyBlocksControl()) return\n", ""),
    ("    partyRateNudge = null\n", ""),
    ("    publishPartyPlayback(rate = next)\n", ""),
    ("    if (isPartySynced) return\n", ""),
    ("            val targetPositionMs = if (isPartyControlLocked) {\n"
     "                ownSeekTarget(requestedPositionMs) ?: return@rememberUpdatedState\n"
     "            } else {\n"
     "                requestedPositionMs\n"
     "            }\n",
     "            val targetPositionMs = requestedPositionMs\n"),
)

def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != SHA:
        raise SystemExit("REFUSE: source is not approved pinned upstream")
    initial = set(git(root, "diff", "--name-only").splitlines())
    if not WAVE1.issubset(initial) or not WAVE2A.issubset(initial):
        raise SystemExit("REFUSE: approved Wave1 and Wave2A patches not present")
    if not initial.issubset(WAVE1 | WAVE2A | GITLINKS):
        raise SystemExit("REFUSE: unrelated pre-existing modified files")
    p = root / REL
    if not p.is_file() or p.is_symlink() or git(root, "hash-object", str(p)) != EXPECTED_BLOB:
        raise SystemExit("REFUSE: upstream gesture source SHA differs from approved upstream")
    original = p.read_text(encoding="utf-8")
    patched = original
    for before, after in EDITS:
        if patched.count(before) != 1:
            raise SystemExit("REFUSE: unexpected gesture source anchor: " + before[:80])
        patched = patched.replace(before, after, 1)
    for legacy in (
        "isPartyControlLocked", "toggleOwnPlayback", "publishPartyPlayback",
        "ownSeekTarget", "isPartySynced", "partyRateNudge", "partyBlocksControl",
    ):
        if legacy in patched:
            raise SystemExit("REFUSE: native Party gesture dependency remains: " + legacy)
    for required in (
        "playerController?.pause()", "playerController?.play()",
        "playerController?.seekBy(offsetMs)", "handleDoubleTapSeek(",
        "activateHoldToSpeed()", "deactivateHoldToSpeed()",
        "commitHorizontalSeek = rememberUpdatedState",
        "scheduleProgressSyncAfterSeek()", "PlayerSurfaceGestureCallbacks(",
    ):
        if required not in patched:
            raise SystemExit("REFUSE: normal gesture function lost: " + required)
    p.write_text(patched, encoding="utf-8")
    changed = set(git(root, "diff", "--name-only").splitlines())
    if changed != initial | {REL}:
        raise SystemExit("REFUSE: out-of-scope changed paths")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2B1_GESTURES_PATCH=PASS")
    print("NORMAL_PLAYBACK_GESTURES_RETAINED=YES")
    print("OTHER_NATIVE_PARTY_EFFECTS_STILL_PRESENT=YES")
    print("PRIVATE_TOGETHER_CODE_NOT_USED=YES")

if __name__ == "__main__":
    main()
