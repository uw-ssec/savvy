# Deprecation Policy

Releases here are dated, not numbered by impact — see the [versioning policy](versioning.md). A dated version cannot tell a user that something they depend on is about to disappear, so this document does that job instead.

> **Reviewers:** the 90-day figure below is a proposal introduced with this policy, not a decision the team made previously. Please push on it if you think it should be longer or shorter.

## What this policy protects

**Names.** Skill names, command names, agent names, and plugin names. These are what a user types or installs, so a rename is indistinguishable from a removal from where they sit.

**Skill intent.** The job a skill does and the prompts it fires on. A skill can keep its name, keep its description, and still stop doing what someone relied on it for — and nothing in the diff looks alarming.

## The intent test

Before merging a change to a skill, answer one question:

> Does a user's existing prompt still reach the same behavior?

**Yes — intent preserved.** Ship it normally.

- Typo and grammar fixes
- Tightened or clarified wording
- Added references or examples
- Corrected links

**No — intent broken.** Follow the deprecation path below.

- Narrowing the trigger language so the skill stops firing on prompts it used to catch
- Changing what the skill produces
- Dropping a capability it used to have
- Repurposing it toward a different task

## The deprecation path

Two routes. **Route 1 is the default.**

### Route 1 — ship it as a new skill (default)

Add the changed behavior under a new name and deprecate the old skill on the clock below. During the overlap a user gets both behaviors, and nothing breaks underneath them. Prefer this whenever intent has genuinely changed.

### Route 2 — deprecate in place (fallback)

Keep the name and change the behavior, having announced it first and served the full notice period. Use this only where a parallel skill would confuse more than it helps — two near-identical skills competing for the same prompts, for instance.

### Commands, agents and whole plugins

Both routes apply to **commands, agents and plugins** by analogy. Route 1 means shipping the replacement under its new name alongside the old one; Route 2 means changing it in place once the notice period has run. The clock and the three required artifacts are identical — only the file holding the deprecation note differs.

## The clock

> A deprecation takes effect — the thing is removed, or an in-place change ships — no earlier than **both** the next release **and** 90 days after the deprecation was announced. Whichever comes later governs.

**A deprecation is announced when the pull request carrying the deprecation note and the changelog entry merges.** That merge starts the 90-day count. The release that subsequently carries that announcement to users satisfies the release clause.

**A micro release counts.** `26.11.1` satisfies the release clause exactly as `26.12.0` does. Letting it count costs nothing, because the two conditions are conjunctive — the 90-day floor still has to elapse, so cutting a quick micro cannot shorten anyone's notice.

Both conditions, not either. Releases here have no fixed cadence, so each clause covers a different failure:

- The **release clause** means a fast run of releases cannot retire something in a week just because two versions shipped.
- The **90-day clause** means a slow stretch still gives users real calendar time to notice.

**A quiet period does not unlock removal.** If 90 days pass and no release has shipped, the thing stays. Elapsed time alone is never sufficient — a release must also have happened.

**This gates Route 2 as well.** Deprecating in place removes nothing, but the behavior change is the gated event: it ships only once both conditions are met. An in-place change that lands before the clock expires is the thing this policy exists to prevent, whether or not a file disappeared.

## What a deprecation requires

Every deprecation, on either route, ships with all three:

1. **A note in the affected file** — the skill's `SKILL.md`, the command's or agent's markdown file, or the plugin's `README.md` when a whole plugin is being retired. It states what is deprecated, what to use instead, and the **earliest removal date**, which is 90 days from the merge written out in full, together with the release rule. For example:

   > *Deprecated 2026-11-20. Removable no earlier than 2027-02-18, and not before the first release on or after that date. Use `new-skill-name` instead.*

   Write the date, not a release number. Under CalVer with no fixed cadence, nobody knows at announcement time what the qualifying release will be called.

2. **A `#### Deprecated` entry in `CHANGELOG.md`**, nested under that plugin's `###` section.
3. **A line in the release announcement**, so it reaches users who read release notes and never read the repository.

**If nothing replaces it**, say so explicitly and say why — "no replacement; this skill is obsolete because X" is a complete answer. The clock and all three artifacts apply unchanged.

### Removing a whole plugin

A plugin's entry in `.claude-plugin/marketplace.json` **stays until the clock expires**, even after the plugin is announced as deprecated. Removing the catalog entry early breaks resolution for everyone who already installed it, which is the outcome the notice period exists to prevent.

## The honest limit

A rename is mechanically checkable: the identifier is right there in the diff, and a script could catch it.

Intent is not. Whether a reworded skill still does the same job is a judgment made by the person writing the change and the person reviewing it, and reasonable people will sometimes disagree. This policy does not pretend otherwise, and no CI check validates it today. What it does is make the question explicit and put it in front of a reviewer, which is the part that was missing.

The author's assertion about intent belongs in the pull request template.

## See also

- [Versioning policy](versioning.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
