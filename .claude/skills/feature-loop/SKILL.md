---
name: feature-loop
description: Use when the owner asks Claude to coordinate review and verification of a feature or bug in this repository.
---

# Feature loop

Coordinate the shared Conductor workspace while Codex makes repository changes.
Follow `AGENTS.md` and `CLAUDE.md`. Do not launch `codex exec` from Claude's
shell: that would give this reviewer an indirect repository write path. Give
the owner a self-contained Codex handoff to run in the Codex chat at each
handoff point.

## Inputs and boundaries

- Get the issue number and the delivery brief for substantial work,
  and the intended PR base. Product work targets
  `projects/100th-meridian-prototype-webxr`, the default branch moving forward;
  verify the actual PR base against the current `AGENTS.md` branch matrix
  rather than assuming an older workspace prompt is current.
- Inspect `git status --short`, the current branch, the issue, and the brief.
  Preserve pre-existing changes. Use the single shared local Supabase stack
  and fixed app port only from one Conductor workspace at a time. Before a
  service check, inspect Conductor's active run scripts and confirm the owning
  workspace with the owner or other workspace. `pnpm db:status` shows whether
  the stack runs, not who owns it. Record the handoff in the review notes;
  wait for exclusive access before running tests.
- A Codex handoff states the issue, exact artifact paths, current phase,
  acceptance criteria, requested action, applicable checks, and where to
  record results. Wait for Codex to finish, then independently inspect its
  actual changes and evidence. A reported success alone is insufficient.
- Claude may write throwaway prototypes only outside the repository. Keep
  tracked repository files unchanged. Do not post issue or PR comments without
  the owner's authorization.

## Substantial features

1. **Design and plan.** Confirm that the delivery brief contains the approved
   design, numbered app-visible acceptance criteria, and implementation steps
   mapping criteria to tests. If it is incomplete, hand off preparation to Codex and
   return to this step. Do not start implementation yet.
2. **Independent validation.** Before reading Codex's validation results,
   identify risky technical assumptions from the design and plan. Check them
   through read-only inspection or prototypes under `/tmp/claude-spikes/`.
   Have Codex validate independently in its own chat, keeping its throwaway
   code under `spikes/<issue-number>-<slug>/`. Serialize all checks using the
   fixed app port or local Supabase stack. Compare assumption, method, result,
   and evidence; identify disagreements.
3. **Recommendations.** Check each acceptance criterion against the planned
   verification and identify gaps or risks. Send numbered findings to Codex.
   Codex records dispositions and a plain-language pre-build section in the
   same delivery brief, including validation results and open questions. Review
   it against the plan and evidence. Keep intermediate review rounds and
   handoffs in the session or `.context/`; preserve the approved brief and final
   review in the issue/PR as required by `AGENTS.md`. Repeat once if needed;
   surface any unresolved disagreement.
4. **Owner gate.** Present the review and Claude's independent check to the
   owner. Wait for explicit pre-build confirmation. If the owner requests a
   change, return it to Codex and review the revised artifact before building.
   A request to move faster does not replace confirmation of the actual
   pre-build review.
5. **Build.** Hand the confirmed plan to Codex. Codex chooses
   `subagent-driven-development` only for independent tasks and uses TDD for
   behavior changes. Review each completed change against the confirmed
   criteria and record findings. Do not modify tracked files yourself.
6. **Verify.** Run the checks for the affected surfaces from `AGENTS.md`,
   `package.json`, and `docs/TESTING.md` with mise auto-install
   disabled. For geospatial values, include `test:precision`, guarded local
   `test:db`, and `validate`. For browser behavior, run local `test:e2e` at
   `http://localhost:55000`; Playwright is not a CI gate. For deployment
   helpers, include `deploy:test` and the client-bundle scan after a build.
   Have Codex prepare the guarded local environment before database tests.
   Mark required checks blocked when they cannot run, and do not call the PR
   ready while they remain blocked. Report each unrun check and its limitation.
   Never aim local tests at hosted Supabase.
7. **Review and PR.** Review the complete diff against the actual PR base,
   changed tests, security effects, and any rejected findings. Re-run affected
   checks after fixes. Codex opens the PR; confirm the PR contains no
   throwaway spikes and inspect `gh pr checks`. Report the exact tested SHA,
   coverage, findings, check results, limitations, and app acceptance steps to
   the owner. The owner decides whether to merge.

## Bugs and small changes

For a bug, use `systematic-debugging`: establish the reported symptom and its
cause, then ask Codex for a meaningful regression check when feasible. Use the
shorter design and review cycle allowed by `AGENTS.md` for small, low-risk
changes. A bug that changes auth, geospatial persistence, or public behavior
uses the substantial-feature gates when the decision or risk warrants them.
When no review log is required, have Codex put the cause, regression check or
reason it was infeasible, consequential decisions, and verification results in
the PR description.

## Stop conditions

Ask the owner about product or scope decisions, new paid services, changed
Auth or security semantics, a test contract Codex believes is wrong,
unresolved review disagreements, and a review or fix loop that cannot
progress. A design or pre-build confirmation never authorizes a production
Supabase or Netlify mutation; those require the separate immediate approvals
and preflight in `AGENTS.md`.
