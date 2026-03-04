# Milestone Closeout - Deferred Verification Debt

Last updated: 2026-02-27
Owner: Engineering
Status: Open (intentional deferral)

This file tracks verification items intentionally deferred to technical debt so the milestone can close now and complete verification later.

## Deferred Items

### D-01: Phase 22 frontend map compatibility (UI not shipped yet)

- Scope: Live frontend map screen verification against real backend/env.
- Why deferred: No completed frontend map visualization flow yet.
- Must verify later:
  - requester centered at `(0,0)`
  - mutual-first behavior
  - additive `is_suggestion` metadata handling
  - no frontend runtime/UI regressions
- Exit criteria:
  - frontend map screen implemented and stable
  - manual QA pass recorded with evidence (screenshots + response payload)

### D-02: Phase 21 live fail-closed publish behavior

- Scope: Real Supabase staging run where publish gates fail.
- Why deferred: Environment-level scenario setup and runtime observation not completed in this milestone window.
- Must verify later:
  - blocked run does not publish new version
  - prior served `version_date`/`computed_at` remain intact
- Exit criteria:
  - before/after payload evidence captured
  - pass/fail logged in closeout report

### D-03: Phase 21 diagnostics role/JWT path

- Scope: Service-role write + authenticated read + unauthorized direct write block.
- Why deferred: Requires staged auth role testing across realistic runtime paths.
- Must verify later:
  - successful and blocked compute runs both recorded
  - read RPC returns expected diagnostics payload
  - unauthorized direct table write denied
- Exit criteria:
  - SQL/API evidence attached to closeout report

### D-04: Phase 23 scheduler local-time cadence verification

- Scope: Observe runtime around UTC midnight and local 19:00 windows.
- Why deferred: Time-window testing cost not suitable for current closeout cycle.
- Must verify later:
  - exactly one global recompute at 00:00 UTC
  - local 19:00 jobs perform warm-only behavior (no recompute)
- Exit criteria:
  - scheduler logs for both windows attached

### D-05: Phase 23 safe legacy-drop migration on staging clone

- Scope: Run `backend/sql/v2_phase23_trigger_validation_and_legacy_drop.sql` against realistic dependency states.
- Why deferred: Requires controlled staging DB permutations and migration rehearsal.
- Must verify later:
  - unsafe dependencies trigger fail-closed block
  - drop executes only when all guards pass
- Exit criteria:
  - blocked and allowed execution evidence attached

## Related Product Debt (Frontend Input Quality)

### D-06: Free-text interest/language token drift

- Risk: `code` vs `Code` vs `coding` treated as different values in matching path.
- Near-term mitigation:
  - normalize client input (trim, lowercase, dedupe)
  - add backend normalization safety in profile update path
- Long-term fix:
  - curated tag taxonomy (canonical IDs + display labels)

### D-07: Timezone capture UX incomplete

- Risk: timezone is supported in backend but not fully exposed in frontend setup/edit UX.
- Near-term mitigation:
  - add timezone field in onboarding and profile edit
  - fallback default from browser timezone
- Long-term fix:
  - validated IANA selector + migration/backfill policy for existing users

## Milestone Close Note

Milestone may close with these debts open, but this file must be reviewed and each item marked complete before declaring full production readiness.
