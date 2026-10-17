#!/usr/bin/env python3
"""Stage17 P2 Wave2B3: PUBLIC frozen Nuvio only.
Detach remaining native Party panel/seek gates/buttons from player UI and
remove Party rate nudge from reported snapshot; preserves normal player actions.
Cumulative after Waves 1, 2A, 2B1, 2B2. NOT full native Party removal.
"""
import argparse
from pathlib import Path
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
PLAYER = BASE + "features/player/"
UI_PATH = PLAYER + "PlayerScreenRuntimeUi.kt"  # Already modified by Wave2A.
ORIGINAL_BLOBS = {
    PLAYER + "PlayerControls.kt": "67f7cf74faef61498a4d13292fef693e9730a325",
    PLAYER + "PlayerControlActions.kt": "c7718c899c4743ab6b0020cef84c18ab23f6236b",
    PLAYER + "PlayerScreenRuntimePlaybackActions.kt": "eb8a6655f6d7e6161f9b35cb67d23d50f04bb129",
}
PREVIOUS = {BASE + p for p in (
    "SettingsDestinations.kt", "AppShellComponents.kt", "MainAppContent.kt",
    "features/settings/SettingsScreen.kt", "features/settings/SettingsRootPage.kt",
    "StreamDestination.kt", "features/player/PlayerScreenRuntimeUi.kt",
    "features/player/PlayerScreenRuntimeGestureActions.kt",
    "features/player/PlayerScreenRuntimeEffects.kt",
)}
GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def edit(s, old, new=""):
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"REFUSE: native Party UI anchor count={count} expected=1: {old[:75]!r}")
    return s.replace(old, new, 1)

def patch_ui(s):
    if "onPartyClick" in s or "PartyRepository" in s or "partyActive" in s:
        raise SystemExit("REFUSE: Wave2A not already applied to player runtime UI")
    s = edit(s, "        RenderParty(runtime = runtime)\n")
    s = edit(s,
        "                    if (!partyBlocksControl()) playNextEpisode()\n",
        "                    playNextEpisode()\n")
    s = edit(s, """            onScrubFinished = { positionMs ->
                val targetMs = if (isPartyControlLocked) ownSeekTarget(positionMs) else positionMs
                if (targetMs == null) {
                    isScrubbingTimeline = false
                    scrubbingPositionMs = null
                } else {
                    finishTimelineScrub(targetMs)
                    playerController?.seekTo(targetMs)
                    scheduleProgressSyncAfterSeek()
                    publishPartyPlayback(positionMs = targetMs)
                }
            },
""", """            onScrubFinished = { positionMs ->
                finishTimelineScrub(positionMs)
                playerController?.seekTo(positionMs)
                scheduleProgressSyncAfterSeek()
            },
""")
    s = edit(s, """                val seekMs = if (isPartyControlLocked) ownSeekTarget(requestedMs) else requestedMs
                if (seekMs != null) {
                    playerController?.seekTo(seekMs)
                    scheduleProgressSyncAfterSeek()
                    publishPartyPlayback(positionMs = seekMs)
                    skipIntervalDismissed = true
                }
""", """                playerController?.seekTo(requestedMs)
                scheduleProgressSyncAfterSeek()
                skipIntervalDismissed = true
""")
    s = edit(s, "            if (!partyBlocksControl()) playNextEpisode()\n",
                  "            playNextEpisode()\n")
    for forbidden in ("RenderParty", "PartyRepository", "partyBlocksControl",
                      "ownSeekTarget", "isPartyControlLocked", "publishPartyPlayback", "onPartyClick"):
        if forbidden in s: raise SystemExit("REFUSE: old native Party UI reference remains: " + forbidden)
    for required in ("RenderPlaybackOverlays(", "RenderPlayerModals(", "PlayerControlsShell(",
                     "onTogglePlayback = { togglePlayback() }",
                     "onScrubFinished = { positionMs ->", "finishTimelineScrub(positionMs)",
                     "scheduleProgressSyncAfterSeek()", "onSkipInterval = { interval ->",
                     "skipIntervalDismissed = true", "playNextEpisode()"):
        if required not in s: raise SystemExit("REFUSE: normal UI control lost: " + required)
    return s

def patch_controls(s):
    s = edit(s, "import androidx.compose.material.icons.rounded.Groups\n")
    for old in (
        "    onPartyClick: (() -> Unit)? = null,\n",
        "    partyActive: Boolean = false,\n",
        # Remove 24-space tokens BEFORE 20-space to avoid suffix matches.
        "                        onPartyClick = onPartyClick,\n",
        "                        partyActive = partyActive,\n",
        "                    onPartyClick = onPartyClick,\n",
        "                    partyActive = partyActive,\n",
        "    onPartyClick: (() -> Unit)?,\n",
        "    partyActive: Boolean,\n",
    ):
        s = edit(s, old)
    s = edit(s, """                    if (onPartyClick != null) {
                        PlayerHeaderIconButton(
                            icon = Icons.Rounded.Groups,
                            contentDescription = stringResource(Res.string.party_title),
                            buttonSize = metrics.headerIconSize + 16.dp,
                            iconSize = metrics.headerIconSize,
                            onClick = onPartyClick,
                            tint = if (partyActive) MaterialTheme.colorScheme.primary else Color.White,
                        )
                    }
""")
    for forbidden in ("onPartyClick", "partyActive", "Res.string.party_title", "Icons.Rounded.Groups"):
        if forbidden in s: raise SystemExit("REFUSE: PlayerControls still shows native Party: " + forbidden)
    for required in ("internal fun PlayerControlsShell(", "private fun PlayerHeader(", "PlayerToolbar(",
                     "onTogglePlayback: () -> Unit", "onScrubFinished: (Long) -> Unit",
                     "onLockToggle = onLockToggle", "onBack = onBack"):
        if required not in s: raise SystemExit("REFUSE: player control missing: " + required)
    return s

def patch_actions(s):
    s = edit(s, "import androidx.compose.material.icons.rounded.Groups\n")
    s = edit(s, "    onPartyClick: (() -> Unit)? = null,\n")
    s = edit(s, "    partyActive: Boolean = false,\n")
    s = edit(s, """        if (onPartyClick != null) {
            PlayerAction(
                description = stringResource(Res.string.party_title),
                icon = Icons.Rounded.Groups,
                onClick = onPartyClick,
                tint = if (partyActive) MaterialTheme.colorScheme.primary else Color.White,
            )
        }
""")
    for forbidden in ("onPartyClick", "partyActive", "Res.string.party_title", "Icons.Rounded.Groups"):
        if forbidden in s: raise SystemExit("REFUSE: toolbar still uses native Party: " + forbidden)
    if "internal fun PlayerToolbar(" not in s or "onLockToggle = onLockToggle" not in s:
        raise SystemExit("REFUSE: normal player toolbar controls lost")
    return s

def patch_snapshot(s):
    s = edit(s,
        "    val reported = if (partyRateNudge != null) snapshot.copy(playbackSpeed = partyBaseRate()) else snapshot\n",
        "    val reported = snapshot\n")
    if "partyRateNudge" in s or "partyBaseRate" in s:
        raise SystemExit("REFUSE: old native Party playback speed reporting remains")
    if "playbackKey != activePlaybackKey" not in s or "reported.copy(durationMs = playbackSnapshot.durationMs)" not in s:
        raise SystemExit("REFUSE: playback snapshot identity or duration guard changed")
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PINNED:
        raise SystemExit("REFUSE: source is not pinned PUBLIC upstream")
    initial = set(git(root, "diff", "--name-only").splitlines())
    if not PREVIOUS.issubset(initial) or not initial.issubset(PREVIOUS | GITLINKS):
        raise SystemExit("REFUSE: required Waves 1/2A/2B1/2B2 not present or unrelated inputs")
    transforms = {
        UI_PATH: patch_ui,
        PLAYER + "PlayerControls.kt": patch_controls,
        PLAYER + "PlayerControlActions.kt": patch_actions,
        PLAYER + "PlayerScreenRuntimePlaybackActions.kt": patch_snapshot,
    }
    staged = {}
    for rel, transform in transforms.items():
        p = root / rel
        if not p.is_file() or p.is_symlink():
            raise SystemExit("REFUSE: missing/unsafe upstream file: " + rel)
        if rel in ORIGINAL_BLOBS and git(root, "hash-object", str(p)) != ORIGINAL_BLOBS[rel]:
            raise SystemExit("REFUSE: upstream source blob drift: " + rel)
        before = p.read_text(encoding="utf-8")
        after = transform(before)
        if after == before: raise SystemExit("REFUSE: empty file change: " + rel)
        staged[p] = after
    # Write only after ALL source SHA, anchors, and behavior checks pass.
    for p,after in staged.items():
        p.write_text(after, encoding="utf-8")
        print("P2_WAVE2B3_FILE_MODIFIED=" + p.relative_to(root).as_posix())
    actual = set(git(root,"diff","--name-only").splitlines())
    expected = initial | (set(transforms) - {UI_PATH})
    if actual != expected:
        raise SystemExit("REFUSE: changed unexpected paths: " + repr(sorted(actual ^ expected)))
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2B3_PLAYER_UI_SNAPSHOT_PATCH=PASS")
    print("NATIVE_WATCH_PARTY_CORE_STILL_PRESENT=YES")
    print("NATIVE_PARTY_RUNTIME_STATE_STILL_PRESENT=YES")
    print("NO_PRIVATE_TOGETHER_CODE=YES")
    print("NO_APK_PUBLISHED=YES")

if __name__ == "__main__":
    main()
