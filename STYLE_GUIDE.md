# Case Study Style Guide

Every project on the portfolio gets the full case study treatment. This
document defines the structure, tone, and metadata conventions so that
every project page reads as a deliberate piece of work — not a caption
dump with a title stuck on top.

## Scope

This applies to:

- **All current projects** in `projects/` — 4 are done (FWA, Chronos
  World, Crypticon, BYVM), 3 are partial, 12 still need the treatment.
- **All future projects** — write the case study when the project is
  created. Do not stub it and come back later.

## Reference projects

Use these as the gold standard. Match their depth and tone:

| Project | Why it's the reference |
|---------|------------------------|
| `fwa` | Largest scope — multiple sections, video embeds, mixed media. The template everything else is measured against. |
| `chronos-world` | Dense brand system with many sub-brands. Good model for projects with a lot of assets that need grouping. |
| `crypticon` | Multi-year project with mixed design and photography. Good model for projects spanning several years or disciplines. |
| `byvm` | Competition entries. Good model for non-client work — honest about results without underselling the effort. |

## Front matter

Every `project.md` starts with `---` front matter. These fields are
rendered by `build.py` and control sorting, filtering, and display.

### Required fields

```yaml
title: The project title, shown as the H1 on the page
client: The client or brand name
year: 2021-2022            # a year or year range
date: 2022-12              # YYYY-MM for sort ordering (see Sort logic below)
category: Brand Identity   # free text, used as a filter on /work/
division: business         # "business" or "arts"
work_type: client          # client | student | competition | self | volunteer
tags: brand identity, print, packaging   # comma-separated
thumb: 01-logo.jpg         # the card thumbnail image
summary: One sentence shown on the index card and the work grid.
```

### Required for case studies

```yaml
sections: Brand Identity, Social Media, Event Posters   # comma-separated H2 headings
outcome: One sentence stating a verifiable result. Leave empty if there isn't one.
```

`sections` drives the H2 headings in the body. Each section heading in
the body must match an entry in this list, in the same order.

`outcome` is a **verifiable** result — a placing, a measurable impact,
an exhibition selection. "Entered a competition" is not a result.
"Placed in the top five out of 300 entries" is. If there is no
verifiable outcome, leave the field empty; it renders nothing.

### Optional fields

```yaml
role: Creative Director       # appears in the meta row; use when you directed a team
context: Contract             # free text, appears in the meta row and disclaimer
featured: true                # includes the project in the home page "Selected Work" section
```

### Sort logic

Projects sort by `date` (YYYY-MM-DD), then `year`, then `title`. The
`date` field is the primary sort key. Set it to the month the project
was completed or delivered, not when it started. If a project spans
multiple years (e.g. Crypticon 2012-2017), set `date` to the **end**
date so it sorts with the most recent work in that span — but be aware
this can push it above projects that were actually completed later.
Adjust `date` to position a project honestly within the timeline.

## Narrative structure

The body text after the `---` follows a consistent arc. Not every
project will fill every beat, but the order stays the same.

### 1. Opening paragraph(s)

What the project was, who it was for, and what the constraints were.
Write in first person. Name the client, the role, the time period, and
the core problem in the first three sentences. Do not bury the lede.

**Example** (from FWA):
> FWA — Fantasy Wrestling Alliance — is the flagship product of JCMG
> Fantasy Sports: a fantasy wrestling promotion where players manage
> rosters, cut promos, and compete across multiple in-game
> organisations. I served as Creative Director from November 2021 to
> the end of December 2022, brought in to rebuild the brand at every
> level.

### 2. Context paragraph(s)

What existed before, what the brief was, what made it hard. This is
where constraints go — no budget, a monthly cadence, a volunteer team,
a six-day broadcast schedule. Be specific about what made the project
difficult, not vague.

### 3. Result paragraph

A short paragraph stating what happened. Did it work? Did it not? Be
honest. The BYVM and Chronos World case studies are explicit that
things didn't go perfectly — that honesty is part of the voice.

### 4. Section headings (H2)

Each `## Heading` matches an entry in the `sections` front matter field.
The body text under each heading explains what the work was, how it was
made, and what it needed to achieve. Then a grid or image embed renders
the visual assets for that section.

### 5. Closing paragraph (optional)

A short wrap-up after the last section. Not every project needs one —
FWA ends on its last section, Chronos World ends with a reflection on
the body of work. Use it only when there's something to say that the
sections didn't cover.

## Tone and voice

- **First person.** "I built," "I designed," "I served as." Not "the
  designer built." Not "we created" unless there was genuinely a team.
- **Past tense.** The work is done. Describe it as completed.
- **Plain language.** No jargon, no agency-speak. "I built the
  company's Discord from nothing" — not "I architected a community
  engagement platform."
- **Specific over general.** "Seventeen in-game promotions each had to
  read as its own brand" — not "multiple brands needed identities."
- **Honest about failure.** If the project didn't succeed, say so. The
  outcome field and the closing paragraph are where this lives. Do not
  spin a loss as a win.
- **No false modesty.** State what you did and what it took. Do not
  undercut the work with qualifiers like "just" or "simply."
- **Short sentences for impact.** "It worked." "The network did not
  survive." Let the short sentences land.

## Image captions

Every image declaration in the front matter gets a caption. Captions
appear as figure text under the rendered image.

### Rules

1. **Describe what the image actually shows**, not just what it is.
   "Tier 1" is a label. "Bronze-tone hexagonal badge, the entry-level
   Patreon support tier" is a caption.
2. **Be specific about visual content.** Name the elements — colors,
   motifs, layout, treatment. A viewer who can't see the image should
   understand it from the caption.
3. **State the purpose when it's not obvious.** "Used as a stream
   interstitial" tells the reader why this piece exists.
4. **No duplicate captions across blocks.** The `audit.py` script
   flags duplicate captions. Each caption must be unique.
5. **No template captions.** "Show logo" repeated ten times is a
   template. Each logo gets its own description of its visual treatment.
6. **`[thumb-only]` tag** marks an image that is used only as the
   card thumbnail and should not be rendered in the page body. Use it
   for the `thumb` image when it's not also a body figure.

### Caption format

```
filename.jpg: Subject — specific visual description, purpose or context
```

**Good:**
```
30-logo-fireside-tales.png: Fireside Tales — illustrated crest with campfire and tent, warm storybook aesthetic
```

**Bad:**
```
30-logo-fireside-tales.png: Fireside Tales — show logo
```

## Photo blocks

Group related images into named photo blocks in the front matter:

```yaml
photos-brand-core:
  01-logo.jpg: Primary logo — wordmark in custom lettering
  02-mascot.jpg: Mascot character — custom illustration in brand colors
photos-event-posters:
  03-spring.jpg: Spring Event — floral poster with hand-drawn typography
  04-summer.jpg: Summer Event — bold color blocking with sun motif
```

Render a block in the body with:

```markdown
[[grid:block-name]]
```

Optional size hints: `[[grid:block-name:large]]`, `:xl`, `:wide`,
`:med`, `:feature`.

### Block naming

- Use `photos-` prefix followed by a short descriptive name:
  `photos-brand-core`, `photos-ppv-headers`, `photos-show-logos`.
- Group by purpose, not by file numbering. The file numbers are
  arbitrary; the blocks should reflect how the work is organized.

## Video embeds

YouTube videos are embedded with:

```markdown
[[youtube:https://youtu.be/VIDEO_ID|Caption — what the video shows]]
```

Local `.mp4` files are referenced in the front matter but never
deployed — they're gitignored and too large for Cloudflare. The build
renders them as a download link if present, but YouTube embeds are the
primary video display method.

## Audit

Run `python audit.py` after every change. It checks for:

- Duplicate captions across photo blocks
- Missing image files referenced in front matter
- Other content issues

The target is always **0 errors, 0 warnings**. Do not silence warnings
— fix the underlying issue.

## Pre-deploy checklist

Before deploying a new or updated case study:

1. `python audit.py` — 0 errors, 0 warnings
2. `python build.py` — builds without errors
3. Front matter has all required fields including `sections` and `outcome`
4. Every image has a specific, unique caption (not a label or template)
5. Body text follows the narrative arc (opening, context, result, sections)
6. Tone is first person, past tense, plain language, honest
7. `date` field positions the project correctly in the timeline
8. `thumb` image is clean and reads well at small card size

## Project status

All projects now have the full case study treatment — `sections` and
`outcome` fields are present, narratives follow the arc, and captions
are specific and unique.

| Project | Status |
|---------|--------|
| fwa | Done (reference example) |
| chronos-world | Done |
| crypticon | Done |
| byvm | Done |
| 3gs-coffeeshop | Done |
| advent-antiquity | Done |
| alpine-tech | Done |
| biztech-rx | Done |
| cloudlifter-media | Done |
| david-carson-study | Done |
| poetry-northwest | Done |
| product-mockups | Done |
| rain-city-brew | Done |
| rain-city-brew-posters | Done |
| rainier-festival | Done |
| stevens-pass | Done |
| vector-illustration | Done |
| vibrations | Done |
| vibrations-magazine | Done |
