#!/usr/bin/env python3
"""Stage17 P2 Wave2C1b — public-only removal of the legacy player Party bridge.

Requires frozen NuvioMedia/NuvioMobile and approved cumulative source patches:
Wave1, Wave2A, Wave2B1, Wave2B2, Wave2B3, Wave2C1a.
Only deletes the legacy player runtime Party bridge and removes its six private
state fields from a TEMPORARY public source checkout. The features/party module,
Party navigation and all private Together source remain OUT OF SCOPE.
"""
import argparse
from pathlib import Path
import re
import subprocess

PINNED_UPSTREAM = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
PLAYER = BASE + "features/player/"
BRIDGE = PLAYER + "PlayerScreenRuntimeParty.kt"
STATE = PLAYER + "PlayerScreenRuntimeState.kt"
GESTURES = PLAYER + "PlayerScreenRuntimeGestureActions.kt"
PLAYBACK = PLAYER + "PlayerScreenRuntimePlaybackActions.kt"
ORIGINAL_BRIDGE_SHA = "a7226df096c0ba7c66e0e89c7acd7f183d9ad59f"
ORIGINAL_STATE_SHA = "259045606e806f2fe0e6b2d5905cfd0e8d24a09f"
PREVIOUS = {BASE + name for name in (
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
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
PARTY_ONLY_FIELDS = """    var showPartyPanel by mutableStateOf(false)
    var partyBehind by mutableStateOf(false)
    var partyBehindMs by mutableStateOf<Long?>(null)
    var partyRateNudge: Float? = null
    var partyPreviousKey: String? = null
    var partyAppInBackground = false
"""
FIELDS = (
    "showPartyPanel", "partyBehind", "partyBehindMs", "partyRateNudge",
    "partyPreviousKey", "partyAppInBackground",
)
NORMAL_HELPER = """internal fun PlayerScreenRuntime.currentNormalPlaybackPositionMs(): Long {
    val snapshot = playbackSnapshot
    if (!snapshot.isPlaying || snapshot.isLoading) return snapshot.positionMs
    val elapsedMs = playbackSnapshotMark?.elapsedNow()?.inWholeMilliseconds?.coerceIn(0L, 1_000L) ?: 0L
    return snapshot.positionMs + (elapsedMs * snapshot.playbackSpeed).toLong()
}
"""
# Symbols defined by the deleted runtime bridge. In the approved post-Wave2C1a
# tree, none may be referenced in another Kotlin file, except the six fields
# being removed from the runtime state file.
BRIDGE_ONLY_SYMBOLS = (
    "isPartySynced", "isPartyControlLocked", "partyBlocksControl",
    "toggleOwnPlayback", "ownSeekTarget", "currentPartyMedia",
    "currentPartyStream", "partyBaseRate", "currentPlaybackPositionMs",
    "publishPartyPlayback", "startParty", "BindPartyEffects", "RenderParty",
    "clearPartyNudge", "applyPartyPaused", "handlePartyMediaChange",
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("REFUSE_P2_WAVE2C1B: " + message)


def scan_external_symbols(root: Path) -> int:
    raw = subprocess.check_output([
        "git", "-C", str(root), "ls-files", "-z", "--", "*.kt"
    ])
    count = 0
    for name in raw.split(b"\x00"):
        if not name:
            continue
        rel = Path(name.decode("utf-8"))
        if rel in (Path(BRIDGE), Path(STATE)):
            # The six fields still exist until next_state is written below.
            # next_state is separately checked for zero legacy fields.
            continue
        path = root / rel
        if not path.is_file() or path.is_symlink():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        symbols = BRIDGE_ONLY_SYMBOLS + FIELDS
        for symbol in symbols:
            if re.search(r"\b" + re.escape(symbol) + r"\b", content):
                raise SystemExit(
                    "REFUSE_P2_WAVE2C1B: external legacy symbol: "
                    + symbol + " in " + rel.as_posix()
                )
        count += 1
    return count


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED_UPSTREAM,
            "not the frozen public upstream")
    require(not git(root, "diff", "--cached", "--name-only"),
            "unexpected staged changes in temporary checkout")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(before), "cumulative previous Waves not applied")
    require(before.issubset(PREVIOUS | ALLOWED_GITLINKS),
            "unexpected tracked file modifications")
    bridge, state = root / BRIDGE, root / STATE
    gestures, playback = root / GESTURES, root / PLAYBACK
    for path in (bridge, state, gestures, playback):
        require(path.is_file() and not path.is_symlink(),
                "required public file missing or unsafe: " + str(path))
    require(git(root, "hash-object", str(bridge)) == ORIGINAL_BRIDGE_SHA,
            "legacy Party bridge changed from frozen upstream")
    require(git(root, "hash-object", str(state)) == ORIGINAL_STATE_SHA,
            "legacy Party state changed from frozen upstream")
    state_text = state.read_text(encoding="utf-8")
    require(state_text.count(PARTY_ONLY_FIELDS) == 1,
            "six native Party state fields differ from frozen upstream")
    next_state = state_text.replace(PARTY_ONLY_FIELDS, "", 1)
    require("var playbackSnapshotMark: TimeMark? = null" in next_state,
            "normal playback timing state missing")
    require("var pendingSeekTarget: Pair<Long, TimeMark>? = null" in next_state,
            "normal seek state missing")
    require("var showStreamInfo by mutableStateOf(false)" in next_state,
            "normal player UI state missing")
    for symbol in FIELDS:
        require(not re.search(r"\b" + symbol + r"\b", next_state),
                "Party-only field remains in player state: " + symbol)

    playback_text = playback.read_text(encoding="utf-8")
    gestures_text = gestures.read_text(encoding="utf-8")
    require(playback_text.count(NORMAL_HELPER) == 1,
            "Wave2C1a normal playback helper not present exactly once")
    require(gestures_text.count("        ?: currentNormalPlaybackPositionMs()\n") == 1,
            "Wave2C1a normal gesture call missing")
    require("currentPlaybackPositionMs()" not in gestures_text,
            "normal player gesture still depends on Party helper")
    for expected in ("playerController?.pause()", "playerController?.play()",
                     "playerController?.seekBy(offsetMs)",
                     "scheduleProgressSyncAfterSeek()"):
        require(expected in gestures_text,
                "normal playback gesture unexpectedly absent: " + expected)
    require("val reported = snapshot" in playback_text,
            "prior Party rate detachment missing")
    examined = scan_external_symbols(root)

    # No writes occur until the complete input, helper, and dependency audit passes.
    state.write_text(next_state, encoding="utf-8")
    bridge.unlink()
    after = set(git(root, "diff", "--name-only").splitlines())
    expected = before | {STATE, BRIDGE}
    require(after == expected, "out-of-scope changed file detected")
    require(not bridge.exists(), "legacy bridge file was not removed")
    require(git(root, "hash-object", str(playback)) != "",
            "normal playback helper source missing")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])

    print("P2_WAVE2C1B_PLAYER_PARTY_BRIDGE_REMOVED=PASS")
    print("P2_WAVE2C1B_PARTY_ONLY_PLAYER_STATES_REMOVED=6")
    print("P2_WAVE2C1B_EXTERNAL_KOTLIN_FILES_SCANNED=" + str(examined))
    print("P2_WAVE2C1B_NORMAL_POSITION_HELPER_RETAINED=YES")
    print("P2_WAVE2C1B_NO_PRIVATE_TOGETHER_CODE=YES")
    print("NATIVE_PARTY_FEATURE_MODULE_STILL_PRESENT=YES")


if __name__ == "__main__":
    main()
