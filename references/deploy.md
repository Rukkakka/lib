# Deploy

How work gets from an idea into `main`. For formatting rules see
[code-style.md](code-style.md).

## Every commit starts from an issue

Open the issue **before** writing the commit, not after. The issue is where the
"why" lives; the commit only has to say what changed and point back to it. A
commit that can't name its issue is a sign the work wasn't scoped yet.

1. **Open an issue** using one of the templates in
   `.github/ISSUE_TEMPLATE/` — never a blank issue.
2. **Cut a branch** off `main`, if you aren't already on one.
3. **Commit to that branch**, referencing the issue number (`Refs #12`).
4. **Open a PR** — `.github/PULL_REQUEST_TEMPLATE.md` fills in automatically.
   Close the issues it resolves from the PR body (`Closes #12`), not from a
   bare commit.

## Never commit to `main`

Commits go on a branch. Always — including one-line fixes, docs, and dependency
bumps. Every change reaches `main` through a PR; there is no "too small for a
PR" change, small ones are just fast PRs.

So before you touch a file, cut the branch:

```
git switch main && git pull
git switch -c chore/repo-setup
```

Name it `<type>/<short-slug>`, where `<type>` is `fix`, `feature`, `docs`,
`chore`, or `task` — whichever describes the bulk of the work.

A branch is not tied to one issue. It can carry as many commits as the work
needs, closing several issues in a single PR, as long as they're related enough
to review together. Split into a second branch when the parts are independent
enough that one could land while the other is still in review.

If you catch yourself already committed on `main`, don't push. Move the work
onto a branch and reset `main` back:

```
git switch -c chore/repo-setup   # takes the commits with you
git branch -f main origin/main
```

## Always use the templates

Both the issue forms and the PR template exist so that the reader who shows up
six months later doesn't have to reconstruct context from a diff. Fill them in;
don't delete sections to save time. If a section genuinely doesn't apply, say
why in one line rather than removing the heading.

Pick the issue template by the kind of work:

| Template      | Label     | Use it for                                       |
| ------------- | --------- | ------------------------------------------------ |
| 🐛 Bug Report | `bug`     | A client not behaving as documented              |
| ✨ Feature    | `feature` | A new client, model, or endpoint                 |
| 📝 Docs       | `docs`    | Docs missing, wrong, or unclear                  |
| 🧹 Chore      | `chore`   | Dependencies, tooling, config, cleanup           |
| ✅ Task       | `task`    | Planned work that fits none of the above         |

The `Type of change` box in the PR template uses these same five names — keep
them in sync with the issue the PR closes.

## One concern per commit

Don't bundle an unrelated fix into a feature commit because it happened to be
in the working tree. Stage deliberately: `git add <path>`, not `git add -A`.
Two concerns means two issues and two commits.

## Before you open the PR

- Imports still work for every client you touched
  (`PYTHONPATH=src python -c 'import clients.<mod>'`).
- `README.md` and `AGENTS.md` module tables updated if a module was added,
  renamed, or removed.
- No credentials, tokens, or internal hostnames in the diff.
- Dependency changes are reflected in `requirements.txt`, and the ranges there
  follow the rule in its header comment.
