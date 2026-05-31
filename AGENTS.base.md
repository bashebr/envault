# AGENTS.md (Base / Parent Standards)

> **What this file is.** A project-agnostic set of engineering standards meant to
> be dropped in at the root of a repository (or a monorepo / org folder) as the
> *parent* `AGENTS.md`. Individual projects place their own `AGENTS.md` in a
> subdirectory; agents read the nearest `AGENTS.md` first and treat this parent as
> the inherited default. Anything a project does not override here still applies.
>
> **How to use it.**
> 1. Copy this file to the directory you want to govern and rename it `AGENTS.md`
>    (or keep it as `AGENTS.base.md` and reference it from the real `AGENTS.md`).
> 2. In each project, add a project-level `AGENTS.md` that fills in the
>    `[PROJECT]` sections below (overview, layout, stack, commands).
> 3. Child files win on conflict. State overrides explicitly, e.g.
>    "Overrides parent: this service uses 4-space indentation."

## Inheritance Model

- **Precedence (highest to lowest):** direct user instruction → project `AGENTS.md`
  → this parent `AGENTS.md` → tool/system defaults.
- A child `AGENTS.md` **extends** this file. It should only restate a rule when it
  is **changing** it, and should say "Overrides parent:" when it does.
- Rules here are intended to be **universal**. Anything language-, framework-, or
  deployment-specific belongs in the project `AGENTS.md`.
- If a rule here does not make sense for a project, the project file must opt out
  explicitly rather than silently ignoring it.

## Core Engineering Principles

- **Smallest reasonable change.** Solve the actual requirement; do not expand
  scope, refactor unrelated code, or add speculative abstractions.
- **Readability over cleverness.** Optimize for the next human (or agent) reading
  the code, not for line count.
- **Consistency with the surrounding code** beats personal preference. Match the
  existing style of the file and module you are editing.
- **No dead weight.** Do not add unused dependencies, exports, flags, or config.
  Remove things you make obsolete.
- **Fail loudly in code, clearly to users.** Surface errors with actionable
  messages; never swallow exceptions silently.
- **Keep modules small and purpose-specific.** One clear responsibility per file.

## Code Conventions

These apply to all languages unless a project file overrides them.

- **Declare imports/dependencies at the top of the module.** Do not import inside
  functions, methods, or conditional blocks. The only acceptable exception is
  breaking a genuine circular import, and that should be fixed by restructuring
  first. Group imports as: standard library, third party, then local/first-party.
  Enforce this with a linter where the language supports it
  (e.g. Python/Ruff `PLC0415`, ESLint `import/first`).
- **Add docstrings/doc comments when necessary, not everywhere.** Document any
  public module, class, function, or exported symbol whose purpose or contract is
  not obvious from its name and signature. Skip docs for trivial,
  self-explanatory helpers rather than restating the code. Keep them concise and
  focused on intent, non-obvious parameters, return values, and raised errors.
- **No narration comments.** Comments explain *why* (intent, trade-offs,
  constraints), never *what* the next line literally does.
- **Names communicate intent.** Prefer descriptive names over abbreviations;
  avoid single-letter names outside tight loops/math.
- **Pure where practical.** Isolate side effects (I/O, network, global state) from
  pure logic so the logic stays testable.
- **Handle errors explicitly.** Catch narrowly; convert low-level failures into
  meaningful, user-facing messages at the boundary layer.
- **Never hardcode secrets.** No tokens, passwords, or keys in source or fixtures.
- **Formatting is automated.** Use the project's configured formatter/linter as
  the source of truth; do not hand-format against it.

## Standard SDLC (follow for every change)

1. **Understand** the requirement and the existing code paths it touches.
2. **Design** the smallest reasonable approach; note trade-offs if non-trivial.
3. **Implement** in focused, reviewable units.
4. **Test** — add or update automated tests that would fail without your change.
5. **Verify** — run the full check suite locally: tests, linter, formatter check,
   and type checker (whichever the project defines).
6. **Document** — update `AGENTS.md`, `README.md`, and inline docs when behavior,
   structure, commands, or dependencies change.
7. **Commit** only after the above pass. Never commit code that fails tests or
   lint.

Keep each change scoped to one logical concern. If you discover unrelated issues,
note them rather than fixing them in the same change.

## Testing Standards

- Every behavioral change ships with tests that exercise it.
- A test must be able to fail: confirm it fails before the fix / passes after.
- Prefer deterministic, isolated tests. Mock external services (network, cloud,
  third-party APIs); do not depend on live systems in the default suite.
- Use temporary/isolated working directories for filesystem tests; never touch the
  real working tree or user files.
- Keep tests readable — they are documentation of intended behavior.

## Version Control & Commits

- Make small, coherent commits with imperative, descriptive subject lines that
  explain the *why*.
- Do not commit generated artifacts, local environment files, or secrets.
- Do not amend or rewrite history that has already been pushed/shared unless the
  user explicitly asks.
- Respect the user's commit-metadata preferences (e.g. trailers/co-authors) — do
  not add them unless requested.
- Never run destructive git operations (force push, hard reset) without an
  explicit request.

## Security & Safety

- Treat all secrets as radioactive: never log, print, or echo them; keep their
  lifetime short.
- Keep secret-bearing and environment files out of version control via
  `.gitignore`.
- Validate and bound untrusted input (size, encoding, type) before processing.
- Preserve existing security and threat-model behavior when refactoring; if a
  change weakens it, call that out explicitly.
- Prefer well-maintained, standard libraries for cryptography and auth over
  hand-rolled implementations.

## Documentation Expectations

- `README.md` is the user-facing source of truth; keep usage and setup current.
- The project `AGENTS.md` is the contributor/agent source of truth; keep its
  layout, stack, and command sections accurate as the project evolves.
- When you change how something is built, run, or deployed, update the docs in the
  same change.

---

## [PROJECT] Sections to fill in per project

Copy these headings into the project-level `AGENTS.md` and complete them. Leave
them out of this parent file.

- **Project Overview** — what it is, who uses it, key constraints.
- **Repository Layout** — directories and important files.
- **Technology Stack** — language version, frameworks, key dependencies.
- **Build, Install, and Run** — exact, copy-pasteable commands.
- **Runtime Architecture** — modules/components and how they interact.
- **Project-specific conventions & overrides** — anything that differs from this
  parent (state "Overrides parent:" explicitly).
- **Testing instructions** — how to run the suite and known gaps.
- **Security considerations** — the concrete threat model for this project.
- **Deployment & release** — how artifacts are built, published, and versioned.
