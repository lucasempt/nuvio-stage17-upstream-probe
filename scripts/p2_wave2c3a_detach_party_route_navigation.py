#!/usr/bin/env python3
"""Stage17 P2 Wave2C3a: detach PUBLIC legacy PartyRoute navigation only.

Runs on a temporary checkout of frozen PUBLIC NuvioMedia/NuvioMobile after
approved cumulative patches through Wave2C2. Removes the dead legacy Party
screen destination and route registration, but keeps the public Party feature
module, PartyRepository, deep-link parser and the normal player unchanged.
No private Nuvio Together sources are involved.
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

# NAV and ROUTES are not touched by the prior eight patch waves.
UNMODIFIED_BLOBS = {
    NAV: "78fb6c3c3442d93c987f29401372aea3e6b45585",
    ROUTES: "786a891225ef1b8e21ced09c4426f9320c32e943",
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
    "features/player/PlayerScreenArgs.kt",
)}
ALLOWED_GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}

ROUTE_DECL = """@Serializable
data class PartyRoute(
    val code: String = "",
    override val title: String = "",
) : SettingsDestinationRoute

"""
PARTY_DESTINATION = """                entry<PartyRoute> { route ->
                    SettingsDestination(route, navController) { onBack ->
                        PartyScreen(
                            initialCode = route.code,
                            onBack = onBack,
                            onWatch = ::openPartyMedia,
                        )
                    }
                }
"""
DEEP_LINK_OLD = """                    is AppDeepLink.Party -> {
                        appGateController?.appReady?.first { it }
                        navController.navigate(PartyRoute(code = deepLink.code, title = watchPartyTitle)) {
                            launchSingleTop = true
                        }
                        AppDeepLinkRepository.markConsumed(deepLink)
                    }
"""
DEEP_LINK_NEW = """                    is AppDeepLink.Party -> {
                        // Legacy public Party navigation is intentionally retired.
                        // Keep parsing and consuming legacy links; Together owns future invites.
                        AppDeepLinkRepository.markConsumed(deepLink)
                    }
"""
MAIN_REMOVALS = (
    "import com.nuvio.app.features.party.PartyScreen\n",
    "    val watchPartyTitle = stringResource(Res.string.party_title)\n",
)
MAIN_REPLACEMENTS = {
    "if (currentRoute is StreamRoute || currentRoute is PlayerRoute || currentRoute is PartyRoute)":
        "if (currentRoute is StreamRoute || currentRoute is PlayerRoute)",
    "val inPlaybackFlow = currentRoute is StreamRoute || currentRoute is PlayerRoute || currentRoute is PartyRoute":
        "val inPlaybackFlow = currentRoute is StreamRoute || currentRoute is PlayerRoute",
    DEEP_LINK_OLD: DEEP_LINK_NEW,
    PARTY_DESTINATION: "",
}
NAV_OLD = "            subclass(PartyRoute::class, PartyRoute.serializer())\n"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def require(value: bool, reason: str) -> None:
    if not value:
        raise SystemExit("REFUSE_P2_WAVE2C3A: " + reason)


def transform_once(s: str, old: str, new: str, label: str) -> str:
    require(s.count(old) == 1, "non-unique upstream source anchor " + label)
    return s.replace(old, new, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    root = parser.parse_args().source.resolve(strict=True)

    require(git(root, "rev-parse", "HEAD") == PINNED, "wrong public upstream revision")
    require(not git(root, "diff", "--cached", "--name-only"), "unexpected staged changes")
    before = set(git(root, "diff", "--name-only").splitlines())
    require(PREVIOUS.issubset(before), "Wave2C2 and all predecessors not applied")
    require(before.issubset(PREVIOUS | ALLOWED_GITLINKS), "unrelated prior file changes")
    require(not (root / BRIDGE).exists(), "Wave2C1b Party bridge still present")
    for path in (MAIN, NAV, ROUTES, STATE, PLAYBACK, PARTY_SCREEN, PARTY_REPO):
        require((root / path).is_file() and not (root / path).is_symlink(),
                "missing or unsafe public Kotlin source: " + path)
    for path, frozen in UNMODIFIED_BLOBS.items():
        require(git(root, "hash-object", str(root / path)) == frozen,
                "frozen public Kotlin file changed: " + path)
    require("onOpenPartyMedia" not in (root / MAIN).read_text(encoding="utf-8"),
            "Wave2C2 callback detachment not present")
    require("showPartyPanel" not in (root / STATE).read_text(encoding="utf-8"),
            "Wave2C1b player states not cleaned")
    require("currentNormalPlaybackPositionMs" in (root / PLAYBACK).read_text(encoding="utf-8"),
            "normal playback position helper missing")

    main_text = (root / MAIN).read_text(encoding="utf-8")
    nav_text = (root / NAV).read_text(encoding="utf-8")
    route_text = (root / ROUTES).read_text(encoding="utf-8")
    require(main_text.count("PartyRoute") == 4, "unexpected PartyRoute references in app")
    require(nav_text.count("PartyRoute") == 2, "unexpected PartyRoute serializer references")
    require(route_text.count("PartyRoute") == 1, "unexpected PartyRoute declarations")
    require(main_text.count("AppDeepLink.Party") == 1,
            "legacy invite parser entry not unique")

    next_main = main_text
    for old in MAIN_REMOVALS:
        next_main = transform_once(next_main, old, "", "MainApp import/title")
    for old,new in MAIN_REPLACEMENTS.items():
        next_main = transform_once(next_main, old, new, "MainApp nav/flow/deep-link")
    next_nav = transform_once(nav_text, NAV_OLD, "", "serializer")
    next_routes = transform_once(route_text, ROUTE_DECL, "", "route declaration")

    require("PartyRoute" not in next_main+next_nav+next_routes,
            "legacy PartyRoute still referenced after rewrite")
    require("AppDeepLinkRepository.markConsumed(deepLink)" in next_main,
            "legacy link consumption not retained")
    require("is AppDeepLink.Party ->" in next_main,
            "Party deep-link parsing accidentally removed")
    require("fun openPartyMedia(media: PartyMedia)" in next_main,
            "legacy Party function unexpectedly modified")
    require("PartyRepository.events.collect" in next_main,
            "legacy Party notifications unexpectedly modified")
    for sentinel in ("entry<PlayerRoute>", "entry<AccountSettingsRoute>",
                     "navController.navigate(DownloadsRoute", "val inPlaybackFlow"):
        require(sentinel in next_main, "normal navigation unexpectedly missing: " + sentinel)
    require("subclass(PlayerRoute::class, PlayerRoute.serializer())" in next_nav,
            "normal player state serializer unexpectedly missing")
    require("data class DownloadsRoute(" in next_routes,
            "normal library route unexpectedly missing")
    for path, content in ((MAIN,next_main),(NAV,next_nav),(ROUTES,next_routes)):
        (root / path).write_text(content, encoding="utf-8")

    after = set(git(root, "diff", "--name-only").splitlines())
    expected = before | {NAV, ROUTES}
    require(after == expected, "unexpected out-of-scope paths changed")
    require((root / PARTY_SCREEN).is_file() and (root / PARTY_REPO).is_file(),
            "Party feature removed too early")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE2C3A_PARTY_ROUTE_DETACHED=PASS")
    print("P2_WAVE2C3A_KOTLIN_FILES_TOUCHED=3")
    print("P2_WAVE2C3A_INVITE_PARSER_RETAINED=YES")
    print("P2_WAVE2C3A_LEGACY_PARTY_INVITES_NO_LONGER_OPEN_SCREEN=YES")
    print("P2_WAVE2C3A_NORMAL_PLAYBACK_AND_NAV_PRESERVED=YES")
    print("P2_WAVE2C3A_PARTY_FEATURE_CORE_STILL_PRESENT=YES")
    print("P2_WAVE2C3A_NO_PRIVATE_TOGETHER_CODE=YES")

if __name__ == "__main__":
    main()
