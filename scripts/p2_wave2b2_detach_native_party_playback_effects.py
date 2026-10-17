#!/usr/bin/env python3
"""Stage17 P2 Wave2B2 (PUBLIC upstream only).
Remove ONLY the old Watch Party hooks from player runtime effects, after verified
Waves 1/2A/2B1. Not the final Party removal, not a Together APK or private patch.
"""
import argparse
from pathlib import Path
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
REL = BASE + "features/player/PlayerScreenRuntimeEffects.kt"
EXPECTED_BLOB = "0bedc25821a1ca961a5b48ba4d2fbd649b93063f"
REQUIRED_WAVE_PATHS = {BASE + name for name in (
    "SettingsDestinations.kt",
    "AppShellComponents.kt",
    "MainAppContent.kt",
    "features/settings/SettingsScreen.kt",
    "features/settings/SettingsRootPage.kt",
    "StreamDestination.kt",
    "features/player/PlayerScreenRuntimeUi.kt",
    "features/player/PlayerScreenRuntimeGestureActions.kt",
)}
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
EDITS = (
    ("import com.nuvio.app.features.party.PartyRepository\n", ""),
    ("        if (isPartySynced && PartyRepository.playback.value != null) {\n"
     "            initialSeekApplied = true\n"
     "            return@LaunchedEffect\n"
     "        }\n", ""),
    ("    BindPartyEffects()\n", ""),
    ("            !isScrubbingTimeline && initialSeekApplied && !isPartyControlLocked &&\n",
     "            !isScrubbingTimeline && initialSeekApplied &&\n"),
    ("            publishPartyPlayback(positionMs = seekPositionMs)\n", ""),
    ("            if (playerSettingsUiState.streamAutoPlayNextEpisodeEnabled && nextEpisodeInfo?.hasAired == true && !isPartyControlLocked) {\n",
     "            if (playerSettingsUiState.streamAutoPlayNextEpisodeEnabled && nextEpisodeInfo?.hasAired == true) {\n"),
)
FORBIDDEN_REMAINING = (
    "PartyRepository", "isPartySynced", "isPartyControlLocked",
    "BindPartyEffects", "publishPartyPlayback",
)
PRESERVE_NORMAL = (
    "BindPlayerUiVisibilityEffects()",
    "BindPlayerMetadataAndSkipEffects()",
    "controller.seekTo(targetPositionMs)",
    "controller.seekTo(seekPositionMs)",
    "scheduleProgressSyncAfterSeek()",
    "skipIntervalDismissed = true",
    "cancelNextEpisodeAutoPlay()",
    "playNextEpisode(automatic = true)",
)

def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PINNED:
        raise SystemExit("REFUSE: input is not the frozen public Nuvio upstream")
    before_paths = set(git(root, "diff", "--name-only").splitlines())
    if not REQUIRED_WAVE_PATHS.issubset(before_paths):
        raise SystemExit("REFUSE: prior cumulative Waves 1/2A/2B1 not present")
    if not before_paths.issubset(REQUIRED_WAVE_PATHS | ALLOWED_GITLINKS):
        raise SystemExit("REFUSE: unexpected modified inputs")
    path = root / REL
    if not path.is_file() or path.is_symlink():
        raise SystemExit("REFUSE: runtime effects file unavailable/unsafe")
    if git(root, "hash-object", str(path)) != EXPECTED_BLOB:
        raise SystemExit("REFUSE: runtime effects input blob drift")
    original = path.read_text(encoding="utf-8")
    patched = original
    for anchor, replacement in EDITS:
        if patched.count(anchor) != 1:
            raise SystemExit("REFUSE: expected exactly one runtime effects anchor: " + anchor[:90])
        patched = patched.replace(anchor, replacement, 1)
    for symbol in FORBIDDEN_REMAINING:
        if symbol in patched:
            raise SystemExit("REFUSE: old Party effects symbol remains: " + symbol)
    for symbol in PRESERVE_NORMAL:
        if symbol not in patched:
            raise SystemExit("REFUSE: normal playback behavior appears missing: " + symbol)
    if len(original) - len(patched) != 340:
        raise SystemExit("REFUSE: unexpected effects diff size")

    # Write ONLY after every static gate passes, in this ephemeral public checkout.
    path.write_text(patched, encoding="utf-8")
    after_paths = set(git(root, "diff", "--name-only").splitlines())
    if after_paths != before_paths | {REL}:
        raise SystemExit("REFUSE: unexpected changed paths: " + repr(sorted(after_paths ^ (before_paths | {REL}))))
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2B2_PLAYER_EFFECTS_PATCH=PASS")
    print("NORMAL_INITIAL_SEEK_AUTOSKIP_NEXTEPISODE_RETAINED=YES")
    print("NATIVE_WATCH_PARTY_CORE_STILL_PRESENT=YES")
    print("NO_TOGETHER_PRIVATE_CODE=YES")

if __name__ == "__main__":
    main()
