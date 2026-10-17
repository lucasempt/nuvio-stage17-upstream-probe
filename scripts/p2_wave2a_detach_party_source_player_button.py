#!/usr/bin/env python3
"""P2 Wave2A PUBLIC-UPSTREAM-ONLY: detach old Party stream injection and player toolbar entry.
Cumulative after the previously approved P2 Wave1 settings patch. Not full Party removal.
"""
import argparse
from pathlib import Path
import subprocess

SHA = "229c083cf3db7bab6fda284484f87439eb4e0eb0"
BASE = "composeApp/src/commonMain/kotlin/com/nuvio/app/"
BLOBS = {
    "StreamDestination.kt": "f5d98b287f17cfe4fc74241de14cec2f139e0c99",
    "features/player/PlayerScreenRuntimeUi.kt": "4868311224c66e11d06379a14645a7a54cf9854c",
}
WAVE1 = {BASE + p for p in (
    "SettingsDestinations.kt", "AppShellComponents.kt", "MainAppContent.kt",
    "features/settings/SettingsScreen.kt", "features/settings/SettingsRootPage.kt"
)}
GITLINKS = {"MPVKit", "libass-android", "vendor/TorrServer", "vendor/quickjs-kt"}

def git(root, *args):
    return subprocess.check_output(["git","-C",str(root),*args], text=True).strip()

def change(s, old, new=""):
    if s.count(old) != 1:
        raise SystemExit("REFUSE: Wave2A upstream anchor not unique or missing: " + old[:75])
    return s.replace(old, new, 1)

def stream(s):
    for old in (
        "import androidx.compose.runtime.CompositionLocalProvider\n",
        "import com.nuvio.app.features.party.PartyRepository\n",
        "import com.nuvio.app.features.party.matches\n",
        "import com.nuvio.app.features.party.partyMediaKey\n",
        "import com.nuvio.app.features.streams.LocalSharedStream\n",
        "import com.nuvio.app.features.streams.LocalStreamHighlight\n",
        "import com.nuvio.app.features.streams.SharedStream\n",
    ):
        s = change(s, old)
    begin = "    val partyState by PartyRepository.state.collectAsStateWithLifecycle()\n"
    end = "    Box(modifier = Modifier.fillMaxSize()) {\n"
    if s.count(begin) != 1:
        raise SystemExit("REFUSE: source Native Party state not unique")
    a = s.index(begin)
    b = s.index(end, a)
    removed = s[a:b]
    if not (800 < len(removed) < 1700 and
            "partyMediaKey(" in removed and "sharedStream = remember(" in removed and
            "PartyRepository.sharedStream" in removed):
        raise SystemExit("REFUSE: unexpected Native Party stream state")
    s = s[:a] + s[b:]
    s = change(s, """    Box(modifier = Modifier.fillMaxSize()) {
        CompositionLocalProvider(
            LocalStreamHighlight provides streamHighlight,
            LocalSharedStream provides sharedStream,
        ) {
""", """    Box(modifier = Modifier.fillMaxSize()) {
""")
    s = change(s, "                        saveForReuse = stream != sharedStream?.stream,\n")
    s = change(s, "        }\n        pendingP2pStreamOpen?.let { pending ->\n",
                  "        pendingP2pStreamOpen?.let { pending ->\n")
    a = s.index("    Box(modifier = Modifier.fillMaxSize()) {\n", s.index("    LaunchedEffect(reuseNavigated)"))
    b = s.index("        pendingP2pStreamOpen?.let { pending ->", a)
    block = s[a:b].split("\n")
    for i in range(1, len(block)):
        if block[i].startswith("            "):
            block[i] = block[i][4:]
    s = s[:a] + "\n".join(block) + s[b:]
    for token in ("PartyRepository", "LocalStreamHighlight", "LocalSharedStream",
                  "partyMediaKey", "partySource", "sharedStream", "CompositionLocalProvider"):
        if token in s: raise SystemExit("REFUSE: leftover source Party hook: " + token)
    if "saveForReuse: Boolean = true" not in s or "P2pConsentDialog(" not in s:
        raise SystemExit("REFUSE: normal source/P2P flow lost")
    return s

def player(s):
    for old in (
        "import androidx.lifecycle.compose.collectAsStateWithLifecycle\n",
        "import com.nuvio.app.features.party.PartyRepository\n",
        "    val partyState by PartyRepository.state.collectAsStateWithLifecycle()\n    val partyActive = partyState.party != null\n",
        """            onPartyClick = if (PartyRepository.available.collectAsStateWithLifecycle().value) {
                {
                    showPartyPanel = true
                    controlsVisible = false
                }
            } else {
                null
            },
            partyActive = partyActive,
""",
    ):
        s = change(s, old)
    for token in ("PartyRepository", "partyActive", "onPartyClick", "collectAsStateWithLifecycle"):
        if token in s: raise SystemExit("REFUSE: leftover player Party button: " + token)
    if "onTogglePlayback = { togglePlayback() }" not in s or "RenderParty(runtime = runtime)" not in s:
        raise SystemExit("REFUSE: unintentionally changed player runtime")
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    root = ap.parse_args().source.resolve(strict=True)
    if git(root,"rev-parse","HEAD") != SHA:
        raise SystemExit("REFUSE: unpinned source HEAD")
    initial = set(git(root,"diff","--name-only").splitlines())
    if not WAVE1.issubset(initial) or not initial.issubset(WAVE1 | GITLINKS):
        raise SystemExit("REFUSE: Wave1 not present or unrelated modified paths")
    staged = {}
    for name,blob in BLOBS.items():
        p = root / BASE / name
        if not p.is_file() or p.is_symlink() or git(root,"hash-object",str(p)) != blob:
            raise SystemExit("REFUSE: source file SHA drift: " + name)
        before = p.read_text(encoding="utf-8")
        after = stream(before) if name=="StreamDestination.kt" else player(before)
        if after == before: raise SystemExit("REFUSE: empty patch " + name)
        staged[p] = after
    # Mutate ONLY the temporary clone, once ALL validations pass.
    for p,after in staged.items():
        p.write_text(after,encoding="utf-8")
        print("P2_WAVE2A_FILE_MODIFIED=" + p.relative_to(root).as_posix())
    actual = set(git(root,"diff","--name-only").splitlines())
    expected = initial | {BASE + p for p in BLOBS}
    if actual != expected:
        raise SystemExit("REFUSE: unrelated file mutation: " + repr(sorted(actual ^ expected)))
    subprocess.check_call(["git","-C",str(root),"diff","--check"])
    print("P2_WAVE2A_SOURCE_PLAYER_BUTTON_PATCH=PASS")
    print("NATIVE_WATCH_PARTY_CORE_STILL_PRESENT=YES")
    print("PRIVATE_TOGETHER_CODE_NOT_USED=YES")

if __name__ == "__main__":
    main()
