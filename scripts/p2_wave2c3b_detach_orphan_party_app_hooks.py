#!/usr/bin/env python3
"""Stage17 P2 Wave2C3b: remove orphaned PUBLIC legacy Party app hooks.

Applies ONLY inside a disposable checkout of frozen public NuvioMedia/NuvioMobile,
after all approved waves through Wave2C3a. Removes the unused native Party
playback launch callback, notice collector and related imports from MainAppContent.
Leaves normal playback, deep-link parsing, and the legacy public Party module intact.
Never reads private Nuvio Together sources or changes the public probe itself.
"""
import argparse
from pathlib import Path
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
MAIN = BASE + "MainAppContent.kt"
NAV = BASE + "AppNavigationSupport.kt"
ROUTES = BASE + "navigation/Routes.kt"
BRIDGE = BASE + "features/player/PlayerScreenRuntimeParty.kt"
STATE = BASE + "features/player/PlayerScreenRuntimeState.kt"
PLAYBACK = BASE + "features/player/PlayerScreenRuntimePlaybackActions.kt"
PARTY_SCREEN = BASE + "features/party/PartyScreen.kt"
PARTY_REPO = BASE + "features/party/PartyRepository.kt"
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

OLD_IMPORTS = tuple(
    "import com.nuvio.app.features.party." + name + "\n"
    for name in ("PartyEvent", "PartyMedia", "PartyRepository", "PartySync")
)
# These are source-exact blocks from the pinned PUBLIC upstream. Previous
# approved waves removed their callers while intentionally preserving them.
OLD_OPEN_PARTY = """        fun openPartyMedia(media: PartyMedia) {
            if (navController.currentRoute is PlayerRoute) navController.popBackStack()
            val resumePositionMs = PartyRepository.playback.value
                ?.takeIf { it.mediaKey == null || it.mediaKey == media.key }
                ?.let { PartySync.expectedPositionMs(it, PartyRepository.nowMs()) }
            launchPlaybackWithDownloadPreference(
                type = media.type,
                videoId = media.videoId ?: media.metaId,
                parentMetaId = media.metaId,
                parentMetaType = media.metaType,
                title = media.title,
                logo = media.logo,
                poster = media.poster,
                background = media.background,
                seasonNumber = media.season,
                episodeNumber = media.episode,
                episodeTitle = media.episodeTitle,
                episodeThumbnail = null,
                pauseDescription = null,
                resumePositionMs = resumePositionMs,
                resumeProgressFraction = null,
                manualSelection = true,
                startFromBeginning = resumePositionMs == null,
            )
        }

"""
OLD_PARTY_NOTICES = """        LaunchedEffect(Unit) {
            if (!ownsAppRuntime) return@LaunchedEffect
            PartyRepository.events.collect { event ->
                val message = when (event) {
                    is PartyEvent.MemberJoined -> getString(Res.string.party_member_joined, event.name)
                    is PartyEvent.MemberLeft -> getString(Res.string.party_member_left, event.name)
                    PartyEvent.Removed -> getString(Res.string.party_removed)
                    PartyEvent.Ended -> getString(Res.string.party_ended)
                    is PartyEvent.MediaChanged -> getString(Res.string.party_media_changed, event.media.title)
                    is PartyEvent.ControlChanged -> getString(
                        if (event.hostOnly) Res.string.party_control_host_only else Res.string.party_control_everyone,
                    )
                }
                NuvioToastController.show(message)
            }
        }

"""


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit("REFUSE_P2_WAVE2C3B: " + message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    root = parser.parse_args().source.resolve(strict=True)
    require(git(root, "rev-parse", "HEAD") == PINNED, "unexpected upstream revision")
    require(not git(root, "diff", "--cached", "--name-only"), "staged files present")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(before), "all approved waves through Wave2C3a required")
    require(before.issubset(PREVIOUS | ALLOWED_GITLINKS), "unrelated changed source")
    require(not (root / BRIDGE).exists(), "legacy player Party bridge still present")
    for rel in (MAIN, NAV, ROUTES, STATE, PLAYBACK, PARTY_SCREEN, PARTY_REPO):
        require((root / rel).is_file() and not (root / rel).is_symlink(),
                "missing or unsafe public source: " + rel)
    require("showPartyPanel" not in (root / STATE).read_text(encoding="utf-8"),
            "Wave2C1b player state patch not present")
    require("currentNormalPlaybackPositionMs" in (root / PLAYBACK).read_text(encoding="utf-8"),
            "normal player position helper missing")
    require("PartyRoute" not in (root / NAV).read_text(encoding="utf-8"),
            "Wave2C3a navigation serializer still present")
    require("PartyRoute" not in (root / ROUTES).read_text(encoding="utf-8"),
            "Wave2C3a route still present")

    current = (root / MAIN).read_text(encoding="utf-8")
    require("onOpenPartyMedia" not in current and "PartyRoute" not in current,
            "earlier callback/nav detachments not applied")
    require("is AppDeepLink.Party ->" in current and
            "AppDeepLinkRepository.markConsumed(deepLink)" in current,
            "legacy invite parser/consumption changed")
    for item in OLD_IMPORTS + (OLD_OPEN_PARTY, OLD_PARTY_NOTICES):
        require(current.count(item) == 1, "missing or nonunique frozen code block: " + repr(item[:65]))
    require(current.count("fun openPartyMedia(media: PartyMedia)") == 1,
            "unexpected legacy media callback references")
    require(current.count("PartyRepository.events.collect") == 1,
            "unexpected native Party collector references")
    for symbol in ("PartyEvent", "PartyMedia", "PartyRepository", "PartySync"):
        require(current.count(symbol) == sum(x.count(symbol) for x in
            OLD_IMPORTS + (OLD_OPEN_PARTY, OLD_PARTY_NOTICES)),
            "unaccounted legacy Party symbol: " + symbol)

    updated = current
    for item in OLD_IMPORTS + (OLD_OPEN_PARTY, OLD_PARTY_NOTICES):
        updated = updated.replace(item, "", 1)
    for symbol in ("PartyEvent", "PartyMedia", "PartyRepository", "PartySync", "openPartyMedia"):
        require(symbol not in updated, "native Party hook remains: " + symbol)
    for sentinel in (
        "is AppDeepLink.Party ->", "AppDeepLinkRepository.markConsumed(deepLink)",
        "val onPlay: ContentPlayAction", "launchPlaybackWithDownloadPreference(",
        "entry<PlayerRoute>", "entry<AccountSettingsRoute>",
        "val onCatalogClick: (HomeCatalogSection) -> Unit",
    ):
        require(sentinel in updated, "normal app path unexpectedly missing: " + sentinel)
    require("party_member_joined" not in updated and "party_control_host_only" not in updated,
            "obsolete native Party toast string remains")

    (root / MAIN).write_text(updated, encoding="utf-8")
    require(set(git(root, "diff", "--name-only").splitlines()) == before,
            "changed files outside previously approved scope")
    require((root / PARTY_SCREEN).is_file() and (root / PARTY_REPO).is_file(),
            "Party core accidentally removed")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2C3B_ORPHAN_NATIVE_PARTY_APP_HOOKS_REMOVED=PASS")
    print("P2_WAVE2C3B_PUBLIC_KOTLIN_FILES_TOUCHED=1")
    print("P2_WAVE2C3B_INVITE_PARSER_RETAINED=YES")
    print("P2_WAVE2C3B_NORMAL_PLAYBACK_AND_NAV_PRESERVED=YES")
    print("P2_WAVE2C3B_PARTY_FEATURE_CORE_STILL_PRESENT=YES")
    print("P2_WAVE2C3B_NO_PRIVATE_TOGETHER_CODE=YES")


if __name__ == "__main__":
    main()
