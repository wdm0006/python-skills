# Project Governance

How an open source Python library makes decisions, grants authority, and survives its founders leaving. Pick the lightest model that fits your project's size, then write it down in a `GOVERNANCE.md` at the repo root so expectations are explicit.

## Contents

- [Governance Models](#governance-models)
- [Maintainer Roles](#maintainer-roles)
- [Becoming a Maintainer](#becoming-a-maintainer)
- [Decision-Making](#decision-making)
- [Handling Conflicts](#handling-conflicts)
- [Succession and Bus Factor](#succession-and-bus-factor)

## Governance Models

Three models cover nearly every project. They form a progression, not a ranking; most projects start at BDFL and formalize only when growth demands it.

**BDFL (Benevolent Dictator For Life).** One person (usually the founder) holds final say. Fast and coherent, ideal for a young project with a single driving author. Fails when that person burns out, disappears, or becomes a bottleneck. If you use this, name a successor early (see bus factor).

**Meritocracy / committer model.** Authority is distributed to people who have earned it through contribution. A group of maintainers share commit rights; new maintainers are promoted based on a track record. Scales past a single person while keeping the barrier to authority merit-based. This is the pragmatic default for a growing library.

**Steering committee / council.** An elected or appointed group holds authority over direction, with defined terms and a voting procedure. Appropriate for large, multi-organization projects where no single person or company should dominate. Heavier process; only adopt it when the project's scale genuinely requires shared institutional control.

Whatever the model, document who decides what, and how someone new gains a say.

## Maintainer Roles

Define a small number of roles with clear rights. Typical tiers:

- **Contributor** — anyone who opens an issue or PR. No special access.
- **Triager** — can label, close, and organize issues. A low-risk first step toward maintainership.
- **Maintainer / committer** — merge rights, reviews PRs, shapes the roadmap.
- **Lead / BDFL / committee** — breaks ties and owns final direction.

List current holders of each role in `GOVERNANCE.md` or a `MAINTAINERS.md` file so responsibility is visible and auditable.

## Becoming a Maintainer

Make the path explicit; ambiguity here quietly caps your contributor pipeline. A workable path:

1. **Sustained contribution.** Several substantive, merged PRs over time, plus helpful review or triage activity.
2. **Nomination.** An existing maintainer nominates the candidate, privately or in an issue.
3. **Confirmation.** The maintainer group approves, typically by lazy consensus (below) or a simple majority.
4. **Onboarding.** Grant access, add them to `MAINTAINERS.md`, and walk through release and review conventions.

State the rough bar in writing ("consistent, high-quality contributions over ~3 months") so aspiring maintainers know what to aim for. Promote for judgment and reliability, not just commit count.

## Decision-Making

Match the process to the stakes. Most decisions should be cheap.

**Lazy consensus.** The default for routine changes. A proposal is assumed accepted if no one objects within a stated window (commonly 72 hours). Silence means assent. This keeps the project moving without demanding a vote for every change. Use it for ordinary PRs, minor API additions, and process tweaks.

**RFC process.** For large or hard-to-reverse changes — a significant API redesign, a dependency policy shift, a breaking release — require a written proposal so the tradeoffs are debated in the open. A lightweight RFC flow:

1. Author writes a proposal (a Markdown file in a `rfcs/` directory or a dedicated issue) covering motivation, design, alternatives, and migration impact.
2. A public comment period (e.g. two weeks) for feedback.
3. Maintainers accept, reject, or request revisions, and record the outcome in the RFC.

Reserve RFCs for decisions genuinely worth the overhead; overusing them stalls the project.

**Voting.** A fallback when consensus fails. Define the rule in advance — who votes, what threshold (simple majority, two-thirds), and how ties break (the lead's vote under BDFL, or a coin toss / status-quo-wins under a committee).

## Handling Conflicts

Disagreement is normal; unmanaged conflict is what drives contributors away.

- **Separate technical from interpersonal.** Technical disputes resolve through the decision process above — data, prototypes, and RFCs, not seniority.
- **Assume good faith and keep it in public.** Public, written discussion prevents backchannel decisions and leaves a record. Move only genuinely sensitive matters (conduct, security) private.
- **Have a tie-breaker.** Every model needs a defined way to end a deadlock: the BDFL decides, the committee votes, or the lead maintainer calls it. State this before you need it.
- **Escalate conduct separately.** Behavior that violates the Code of Conduct goes to the conduct contact, not the technical decision process. Keep the two tracks distinct.
- **Document the outcome.** Record what was decided and why, so the same argument does not reopen every quarter.

## Succession and Bus Factor

Bus factor is the number of people who would have to disappear before the project stalls. A bus factor of one is the most common cause of library abandonment. Raise it deliberately:

- **Distribute access.** More than one person must hold merge rights, the PyPI publish token, and the domain/CI credentials. A single-holder secret is a single point of failure.
- **Document the release process.** Anyone with access should be able to cut a release from written instructions, not tribal knowledge.
- **Name a successor.** Under BDFL especially, state who takes over and how. Do this while the founder is active, not in a crisis.
- **Onboard continuously.** Promote maintainers before you are desperate, so knowledge transfers gradually.
- **Plan for graceful handoff.** If the project must wind down, transfer it to a new maintainer or a foundation, or clearly mark it unmaintained and point users to alternatives. Silent abandonment is the worst outcome for downstream users.

The goal is simple: the project should outlive the interest and availability of any single contributor.
