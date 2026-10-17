# Stage17 P2 — Wave 2C1a: read-only preflight

Status: **source-inspection PASS; source patch NOT applied; compilation NOT run**.

## Public upstream provenance

- Source: `NuvioMedia/NuvioMobile` at pinned SHA `229c083cf3db7bab6fda284484f87439eb4e0eb0`.
- Last approved public cumulative build: Wave 2B3, GitHub Actions run [39054159933](https://github.com/lucasempt/nuvio-stage17-upstream-probe/actions/runs/39054159933).
- Public dependency audit: run [39055490623](https://github.com/lucasempt/nuvio-stage17-upstream-probe/actions/runs/39055490623), `STAGE17_P2_WAVE2C1_DEPENDENCY_AUDIT=PASS`, scanned 1,262 Kotlin files, found zero external native runtime references other than the separately handled position helper.

## Preserving normal playback

`PlayerScreenRuntimeParty.kt` contains `PlayerScreenRuntime.currentPlaybackPositionMs()`, currently called from the normal `seekBy` flow in `PlayerScreenRuntimeGestureActions.kt`. The method reads `playbackSnapshot`, returns the snapshot position when paused/loading, otherwise adds bounded elapsed time (up to 1,000 ms) multiplied by playback speed.

The read-only inspection confirmed:
- The existing definition is unique and the method body can be preserved unchanged.
- Exactly one normal gesture call remains after the approved gesture detachment.
- `PlayerScreenRuntimePlaybackActions.kt` has a unique safe insertion location and does not already define the proposed `currentNormalPlaybackPositionMs()` helper.
- `PlayerScreenRuntimeState.kt` retains `playbackSnapshotMark`, used by this method.
- All six native Party-only state fields remain unmodified pending a later, separately validated removal.

## Staged implementation and acceptance gates

1. In a **temporary, public-upstream-only checkout**, apply the already approved Waves 1, 2A, 2B1, 2B2 and 2B3.
2. Preserve the current position helper's body, under a normal-player-only name, in `PlayerScreenRuntimePlaybackActions.kt`. Update only the corresponding normal gesture call. Keep the old Party bridge and fields **unchanged** for this validation wave.
3. Check exact frozen-source hashes, source anchors, touched paths and `git diff --check`.
4. Compile `:androidApp:assembleFullDebug` and check the ordinary seek/playback path with device tests when feasible. Do not infer runtime correctness solely from a successful build.
5. **Only in a later separately approved step**, consider removing the native Party runtime bridge and its six exclusive states after confirming that the normal position helper no longer depends on it.

## Security and scope

This document does **not** contain private Together source, credentials, protocol, patches or APKs. Do not publish private Nuvio Together material in this PUBLIC repository. Never publish Android build output; delete temporary APKs in the ephemeral runner. The private Stage16 branch must remain untouched.

**No execution is authorized by this document.** Manual workflow dispatch and successful build are still required.
