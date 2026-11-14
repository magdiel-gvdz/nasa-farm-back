# Repository requirements for OpenSpec workflows

These requirements apply before every step in the generated skills and take
precedence over conflicting examples below them.

## Commands and project discovery

- Validate every change name against `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` before
  constructing paths or invoking the CLI. Reject invalid names; do not sanitize
  them into another change. Validate store identifiers with the same allowlist.
- Pass arguments through a process argument array with shell execution disabled.
  Never interpolate input into a shell command. If a shell tool is required,
  use only validated identifiers and single-quote each argument using that
  shell's encoding rules. Double quotes alone do not prevent command expansion.
- Read the JSON result of project discovery and check declared-store `status`
  errors first. Report `Declared in` and `Invalid store declaration in` errors
  with their supplied fix, and stop. Only then interpret `root: null` as an
  uninitialized project. Do not initialize a declared but unresolved store.
- Load the selected root's project context, language and artifact rules before
  every proposed write, including small revisions. Fetch artifact instructions
  where needed. This repository requires Spanish prose while retaining the
  structural headings and SHALL/MUST keywords expected by OpenSpec.

## Paths

- Resolve the real OpenSpec root, following symlinks and Windows junctions.
  Before every read, write, directory creation or move, canonicalize its path
  and existing ancestors, including symlinks/junctions. Stop if it escapes the
  operation's expected root. Do not rely on string-prefix comparisons.
- Delta inputs and artifact edits must remain inside the selected change root.
  Main-spec destinations must remain inside the real `openspec/specs` root.
  Archive destinations must remain inside the real `openspec/changes/archive`
  root. Reject absolute capability paths, traversal components and links that
  escape these roots. Check both source and destination immediately before moves.

## Concurrency and recovery

- Serialize all mutating OpenSpec workflows for a root. Acquire
  `openspec/.workflow.lock` using atomic exclusive file creation (for example,
  `O_CREAT | O_EXCL`) before reading snapshots or modifying files. Record an
  ownership token and release only a lock owned by this operation, in a finally
  block. Stop if another owner holds it; never force-remove another owner's lock.
  Nested sync/archive steps share the proven ownership token rather than
  acquiring a second lock. Exploration remains read-only.
- For apply, re-read the task and affected code under the lock, perform and
  verify the implementation, then mark the task complete. Do not mark a task
  complete based only on another agent's task checkbox.
- For sync, stage every capability update before modifying any main spec.
  Validate the complete staged result and recheck source/destination fingerprints
  before publishing. Keep snapshots of original files and a list of newly
  created files. On any publication or validation error, restore original bytes
  and remove only newly created files belonging to this operation; retain the
  active change and report the failure. Never report partial sync as success.
- During archive, hold the same lock through sync, final delta comparison and
  the move. Record delta fingerprints and verify them immediately before moving;
  abort if any changed. Use platform-native directory/move tools with validated,
  canonical paths; the shell examples are illustrative, not portable commands.

These are repository customizations. After `openspec update` or regeneration,
retain this policy and restore each skill's mandatory reference to it.
