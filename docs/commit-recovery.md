# Commit recovery

## Current source is authoritative

The current branch commits the reviewed working tree directly. The older
`ticket-commits.bundle` is retained locally and ignored by Git; it predates the
Claude review corrections. Do not import it over the current implementation.
The notes below describe its historical provenance only.

## Historical recovery bundle

The attached worktree points its `.git` file at the parent project's Git store.
This session could read that store but could not create its `index.lock`, so it
could not advance the attached branch. To preserve the requested history, the
eleven commits were made on a local copy of the same branch and exported as
`ticket-commits.bundle` at the repository root.

For recovery of that earlier snapshot in a separate checkout only:

```sh
git fetch ./ticket-commits.bundle colorado-mud-terrain-e4ea3c35
git merge --ff-only FETCH_HEAD
```

The bundle starts at `d90ec9a` and ends at `c49e086` before this note's final
amendment; inspect `git bundle list-heads ticket-commits.bundle` for the final ID.
It contains exactly one `ticket NN: <title>` commit for each ticket, 01–11.
The worktree already contained the complete uncommitted implementation when this
session began. Ticket 01 therefore snapshots that implementation and shared
evidence; commits 02–11 add criterion-by-criterion ticket status records. The
history preserves the requested ticket order but does not imply each feature was
written incrementally between those commits.

Generated tiles and downloaded GIS inputs are absent from the bundle. Build them
with `npm run setup:bake && npm run bake:scene` after importing.
