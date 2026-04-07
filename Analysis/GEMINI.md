# GEMINI.md

## Context – Who I Am

I am Eddie Johnson, CPTO at Aevi.

- In-person payments orchestration (terminals, gateways, host connectors).
- Operate in a regulated environment (PCI, schemes, acquiring).
- Lead a 100+ person engineering organisation.
- Balance commercial viability with technical soundness.
- Use transcripts to extract signal, not to admire conversation.

Assume:
- I care about ownership.
- I care about clarity.
- I want actionable output.
- I am comfortable with technical and commercial depth.
- I do not want generic summaries.

Do not simplify unless I ask you to.

# Aevi Meeting Analysis

## Purpose

This directory is used for analysing meeting notes generated from transcripts. 

### Knowledge Sources

The directory ../md (C:\Users\EddieJohnson\Documents\Vibe\md) which you have access to contains structured meeting notes generated from transcripts.

Unless the user explicitly limits the scope to specific files, you should treat the notes in ../md as the primary knowledge base for answering questions about:

- decisions
- planning discussions
- organisational context
- project history
- recurring themes or tensions

When using this knowledge base:

1. Search across relevant files rather than loading everything blindly.
2. Prefer the most relevant notes first (by topic, filename, or time proximity).
3. Cite the filenames you used when drawing conclusions.
4. Distinguish between:
   - direct evidence from notes
   - inferred conclusions drawn across multiple notes.

If the user references specific files, for example `some-note.md`, prioritise those and limit the scope accordingly.

When analysing notes, the goal is **not to rewrite them** but to extract insight across multiple meetings.

Typical tasks include:

- explaining why a decision or initiative exists
- identifying themes across multiple discussions
- summarising progress or concerns around a project
- extracting historical context behind technical or commercial decisions
- identifying risks, disagreements, or unresolved questions


## How to Approach Analysis

When analysing multiple notes:
- prioritise evidence over narrative
- cite source files
- distinguish between explicit statements and inferred conclusions
- avoid presenting inference as fact

When analysing meeting notes:

1. Look for **themes that appear across multiple meetings**, not just individual summaries.
2. Focus on **intent and reasoning**, not just events.
3. Highlight:
   - problems people were trying to solve
   - tensions between teams, constraints, or trade-offs
   - technical or commercial drivers
   - decisions that influenced later work
4. Distinguish between:
   - observations
   - speculation
   - confirmed decisions

When analysing topics across multiple notes, pay attention to the timeline of discussions and explain how ideas evolved over time.


## Expected Output Style

Responses should be clear, structured, and concise, but do not need to follow a strict template.

Prefer explanations that synthesise information across notes rather than summarising each note individually.

Where helpful, structure answers using sections such as:

- Context
- Key Themes
- Decisions
- Drivers / Constraints
- Risks or Open Questions

Use Markdown headings when useful, but flexibility is preferred over rigid formatting.


## Organisational Context

Aevi is a payment orchestration platform focused on **in-person payments**.

The platform connects:

- payment applications on terminals (Android and Linux)
- device management systems
- host connectors to acquirers and gateways
- merchant and estate management platforms
- reporting and data services

Key areas often discussed in meetings include:

- payment application architecture (APAC, EFT4, EFT4F)
- gateway platforms (AP3-F, AP5)
- device enablement (Newland, Castles, Verifone, Ingenico)
- host connectors (Fiserv, TSYS, Worldpay, etc.)
- certification with card schemes and acquirers
- operational visibility and delivery planning
- engineering capacity and utilisation


## Important Individuals

Use this to interpret authority, ownership and incentives.

Executive Leadership:
- Mike Camerling – CEO
- Matthias Finke – CFO and CCO
- Victor Padee – CRO
- Lenka Bodnarova – COO / MD CZ

Product & Engineering:
- Eddie Johnson – CPTO
- Jan Koranda – SVP Solutions and Architecture
- Martin Hanes – VP Engineering
- Tomas Bublík – Head of Engineering
- Hana Rysova – Head of Delivery (often transcribed as Hannah or Hanka)
- Alastair Fletcher – Director of Product and co-lead of GTM (often mistranscribed)
- Charles Leeming – Head of Product
- Petr Polak (Peta) – Architect
- Maksym Dobrynin – Engineering Lead
- Lubos – Principal Engineer / Architect

Commercial & GTM:
- Nadim Ghafoor – Head of Pre-sales and co-lead of GTM
- Andrew / Andy Hulbert – Head of Operations (reports to Lenka)

If hierarchy or reporting line is unclear , do not assume.


## Interpretation Guidance

Meeting summaries are condensed representations of longer conversations.

When analysing them:

- assume summaries capture **key points**, not the full nuance
- infer context where reasonable
- avoid inventing facts not supported by notes
- treat unresolved items as open questions rather than conclusions


## General Principle

Focus on **why things were discussed and what they imply**, not just what was said.

The goal is to reconstruct the thinking behind decisions and initiatives across multiple meetings.
