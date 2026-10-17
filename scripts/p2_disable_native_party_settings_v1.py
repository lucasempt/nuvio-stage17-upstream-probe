#!/usr/bin/env python3
"""Stage17 P2 wave 1: remove ONLY upstream native Watch Party SETTINGS entry points.
Public upstream-only, pinned commit; never reads or modifies private Together code.
This is NOT the full native Watch Party removal or a Together build.
"""
import argparse
import pathlib
import subprocess

PINNED = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
EXPECTED = {
    "SettingsDestinations.kt": "f1b2fe8e49ee1b749da73cbb48403035a1e097a8",
    "AppShellComponents.kt": "2b957897c902c477b77337517f08d38c7ae03018",
    "MainAppContent.kt": "b3c7ecd60549742a3dea4746b12e5046f594df5f",
    "features/settings/SettingsScreen.kt": "a70aa5e056c71aa1d2af1b94e52345265a0b457f",
    "features/settings/SettingsRootPage.kt": "b0672f489d533676355cd3837ace6536792d97ff",
}
RULES = {
    "SettingsDestinations.kt": [
        ("import com.nuvio.app.navigation.PartyRoute\n", 1),
        ("import nuvio.composeapp.generated.resources.party_title\n", 1),
        ("    val watchPartyTitle = stringResource(Res.string.party_title)\n", 1),
        ("        onWatchPartyClick = {\n            navController.navigate(PartyRoute(title = watchPartyTitle))\n        },\n", 1),
    ],
    "AppShellComponents.kt": [
        ("    val onWatchPartySettingsClick: () -> Unit = {},\n", 1),
        ("                    onWatchPartyClick = actions.onWatchPartySettingsClick,\n", 1),
    ],
    "MainAppContent.kt": [
        ("                                onWatchPartySettingsClick = { navController.navigate(PartyRoute(title = watchPartyTitle)) },\n", 1),
    ],
    "features/settings/SettingsScreen.kt": [
        ("import com.nuvio.app.features.party.PartyRepository\n", 1),
        ("@Composable\nprivate fun watchPartyRow(onClick: () -> Unit): (() -> Unit)? {\n    val available by PartyRepository.available.collectAsStateWithLifecycle()\n    return onClick.takeIf { available }\n}\n\n", 1),
        ("    onWatchPartyClick: () -> Unit = {},\n", 3),
        ("                        onWatchPartyClick = onWatchPartyClick,\n", 2),
        ("            val watchPartyRowClick = watchPartyRow(onWatchPartyClick)\n", 1),
        ("        val watchPartyRowClick = watchPartyRow(onWatchPartyClick)\n", 1),
        ("                                onWatchPartyClick = watchPartyRowClick,\n", 1),
        ("                            onWatchPartyClick = watchPartyRowClick,\n", 1),
    ],
    "features/settings/SettingsRootPage.kt": [
        ("import nuvio.composeapp.generated.resources.party_settings_description\n", 1),
        ("import nuvio.composeapp.generated.resources.party_title\n", 1),
        ("    onWatchPartyClick: (() -> Unit)? = null,\n", 1),
        ("                    if (onWatchPartyClick != null) {\n                        SettingsGroupDivider(isTablet = isTablet)\n                        SettingsNavigationRow(\n                            title = stringResource(Res.string.party_title),\n                            description = stringResource(Res.string.party_settings_description),\n                            icon = Icons.Rounded.Groups,\n                            isTablet = isTablet,\n                            onClick = onWatchPartyClick,\n                        )\n                    }\n", 1),
    ],
}

def git(root, *parts):
    return subprocess.check_output(["git", "-C", str(root), *parts], text=True).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=pathlib.Path)
    args = ap.parse_args()
    root = args.source.resolve(strict=True)
    if git(root, "rev-parse", "HEAD") != PINNED:
        raise SystemExit("REFUSE: unexpected upstream SHA")
    # Public upstream gitlinks can appear deleted when not initialized. Allow
    # ONLY those four documented gitlink placeholders as pre-existing changes.
    baseline = set(git(root, "diff", "--name-only").splitlines())
    allowed_gitlinks = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}
    if not baseline.issubset(allowed_gitlinks):
        raise SystemExit(f"REFUSE: unexpected initial dirty upstream: {sorted(baseline)}")
    staged = {}
    for rel, expected_blob in EXPECTED.items():
        path = root / BASE / rel
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"REFUSE: required file missing/unsafe: {rel}")
        original_blob = subprocess.check_output(["git", "-C", str(root), "hash-object", str(path)], text=True).strip()
        if original_blob != expected_blob:
            raise SystemExit(f"REFUSE: upstream content drift: {rel}")
        before = path.read_text(encoding="utf-8")
        after = before
        for needle, count in RULES[rel]:
            actual = after.count(needle)
            if actual != count:
                raise SystemExit(f"REFUSE: unexpected {rel} anchor (expected {count}, got {actual})")
            after = after.replace(needle, "")
        if after == before:
            raise SystemExit(f"REFUSE: no change for {rel}")
        for forbidden in ("onWatchPartyClick", "onWatchPartySettingsClick", "watchPartyRow"):
            if forbidden in after:
                raise SystemExit(f"REFUSE: leftover settings symbol in {rel}: {forbidden}")
        staged[path] = after

    # Only write once ALL 5 paths, commit, exact blobs and anchors are validated.
    for path, after in staged.items():
        path.write_text(after, encoding="utf-8")
        print(f"P2_SETTINGS_FILE_MODIFIED={path.relative_to(root)}")
    actual_paths = set(git(root, "diff", "--name-only").splitlines())
    required_paths = {BASE + rel for rel in EXPECTED}
    if actual_paths != baseline | required_paths:
        raise SystemExit(f"UNEXPECTED_DIFF_PATHS={sorted(actual_paths.symmetric_difference(baseline | required_paths))}")
    subprocess.check_call(["git", "-C", str(root), "diff", "--check"])
    print("P2_WAVE1_SETTINGS_PATCH=PASS")
    print("NATIVE_WATCH_PARTY_OTHER_INTEGRATIONS=STILL_PRESENT")
    print("NO_PRIVATE_CODE=YES")
    print("NO_PUBLISHED_APK=YES")

if __name__ == "__main__":
    main()
