# Stage17 P2 — Wave 2C1a: Kotlin helper equivalence check

**Status:** local isolated Kotlin syntax and behavior test **PASS** (7/7). **No Android Gradle build or Android device test has been run for Wave 2C1a. No Kotlin sources have been changed in the public probe or the private Stage16 repository.**

## Context

- Source: public frozen `NuvioMedia/NuvioMobile` commit `229c083cf3db7bab6fda284484f87439eb4e0eb0`.
- Previous cumulative build: Wave 2B3, GitHub Actions run [39054159933](https://github.com/lucasempt/nuvio-stage17-upstream-probe/actions/runs/39054159933), `BUILD SUCCESSFUL`.
- Party dependencies preflight: run [39055490623](https://github.com/lucasempt/nuvio-stage17-upstream-probe/actions/runs/39055490623), 1,262 Kotlin files audited, zero external native runtime references after prior patches.
- See [Wave 2C1a preflight](STAGE17_P2_WAVE2C1A_PREFLIGHT.md).

## Isolated test executed

Compiled and ran a small, standalone Kotlin fixture using the installed Kotlin compiler and the actual helper body identified in the pinned public upstream. It supplied simple fake playback snapshots and a deterministic `TimeMark` implementation. Two functions used the same body with only a different method name:

- Legacy: `PlayerScreenRuntime.currentPlaybackPositionMs()`
- Proposed normal-player helper: `PlayerScreenRuntime.currentNormalPlaybackPositionMs()`

The fixture compared both return values under these conditions:

| Scenario | Legacy | Proposed | Result |
|---|---:|---:|---|
| Paused | 20,000 ms | 20,000 ms | PASS |
| Loading | 20,000 ms | 20,000 ms | PASS |
| Playing, 1x, 500ms elapsed | 20,500 ms | 20,500 ms | PASS |
| Playing, 1.25x, 500ms elapsed | 20,625 ms | 20,625 ms | PASS |
| Playing, 1.5x, 2500ms elapsed (clamped to 1000ms) | 21,500 ms | 21,500 ms | PASS |
| Negative elapsed time (clamped to 0ms) | 20,000 ms | 20,000 ms | PASS |
| No `TimeMark` | 20,000 ms | 20,000 ms | PASS |

`P2_WAVE2C1A_KOTLIN_HELPER_EQUIVALENCE=PASS (7 cases)`

## What this DOES and DOES NOT establish

- **Established:** the copied helper body, with a renamed declaration, compiles and gives equivalent results for these seven deterministic test cases.
- **Not established:** that the cumulative Android source compiles after real code changes; that seek behavior or screen lifecycle is correct on a device; that the old Party bridge can already be removed.
- The public GitHub probe has **not** received any new source-modifying scripts, Kotlin source, APK, private Together code, secrets or credentials.

## Next required gate

A separate authorized source-modification and manual compile gate is needed to (1) move the normal helper to `PlayerScreenRuntimePlaybackActions.kt`, (2) update exactly one remaining normal gesture call, and (3) retain the legacy Party bridge until Android compilation passes. Only after this gate may a distinct removal wave be considered. The GitHub source-modification automation was blocked by tool safety checks in earlier attempts; do not bypass those checks.

## Protected baseline

The private Stage16 `nuvio-together-v4-chat-presence` branch stays on `a72dadd001dfcbc2875fca6431250f567a673ddf`; it must not be modified during public upstream evaluation.
