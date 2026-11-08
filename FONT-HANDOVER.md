# Handover: a custom display font (and style guide) for fabianlanger.nl

For a separate project in which Fabian designs his own font, and then a style guide derived from it.
This document says **where the font is used, why, what it has to feel like, and exactly what files the website needs** to adopt it.
Written 2026-11-07 from the website repo (`fabianlanger-site`, branch `main`, v1).

---

## 1. Fonts on the site today

The live site (v1) uses **two font families**. Everything else seen in prototypes was only for comparison and is not on the site.

| Family | Weights loaded | Where | Intent |
|---|---|---|---|
| **Poppins** (IBS house font) | 300 Light, 400 Regular, 500 Medium, 600 SemiBold | Everything except the two places below: headings (Light), body text (Light/Regular), navigation, buttons, small caps labels (SemiBold, wide tracking), captions, the text inside the animated diagrams | Calm, geometric, readable; ties the site to the IBS house style |
| **Monsieur La Doulaise** (script) | 400 | Only 2 places: **your name in the homepage hero** and the **sign-off "Fabian" under every article** | A personal signature: the one human, handwritten moment on the page |

How Poppins is used (from the code): 29× Light, 4× SemiBold, 1× Medium. All big headings are Poppins Light, e.g. "The full story behind my posts", "Services", "From strategy to solutions", article titles.

**Why the prototypes showed your name twice plus a line underneath:** each font sample showed the same font in three jobs (capitals, mixed-case name, a heading) so you could judge it per job. In reality a font gets one or more *roles*, below.

## 2. Roles the new font could take

The decision for the font project is **which roles it plays**. Each role asks for a different amount of play:

| Role | Where on the site (examples) | Size | How playful can it be? |
|---|---|---|---|
| **R1 · Wordmark** | Your name in the hero; the sign-off "Fabian" | 80–160 px | **Most expressive.** Swashes, ligatures, a one-off. Can be an SVG drawing instead of a font. |
| **R2 · Display headings** | Article titles ("What do we mean by *self-learning*?"), section titles ("Services", "Recent work", "From strategy to *solutions*"), 404 title | 36–96 px | **Expressive but readable.** Contrast and character; swashes only on a few letters or as alternates. |
| **R3 · Pull quotes / closing lines** | "Not everything that *adapts*, learns." · "Confusing concepts make for *crippling policy*." | 30–60 px | **Expressive.** Short lines read slowly; a good place for a swash ligature. |
| **R4 · Big numbers** | Stats: "9+", "6+", "302+", "9+"; numbers 01–04 in the route and the writing index | 30–60 px | **Straight to the point.** Figures must read instantly; character in the curves, not in swashes. |
| Stays Poppins | Body text, navigation, buttons, labels, captions, diagram text, forms | 11–20 px | Not this font: long reading and small UI need calm and IBS consistency. |

**Recommendation:** design for **R1 + R2 + R3** (one family), make **R4** optional (figures 0–9 and "+" in the same style). The minimum viable font is R1 alone (just a wordmark).

One word in a heading is often highlighted with a yellow→red gradient that moves like a reflection while scrolling (e.g. *solutions*, *self-learning*). The font must look good filled with a gradient: avoid hairlines so thin they disappear at ~40 px.

## 3. The feeling to aim for

From the design rounds (references you shared: **Botanica, Miaruka, Mallfom**):

- **Contrast inside the stroke.** Hairline-thin and heavy within one letter; the weight is *felt* in the thick parts, the elegance in the hairlines.
- **Straight and curved movement together.** Strokes run straight and then turn into a curve, a teardrop or a blade; not wobbly.
- **Asymmetric swell.** Like the leaf in the chosen photo corner (decision "3A"): a stroke swells in from a point, carries weight off-centre, and tapers out again.
- **Botanical, not floral.** Leaf-like *terminals and swashes grown from the stroke*; no flowers or leaves added on top.
- **Avoid:** "wonky"/leaning letters, casino-gold luxury, art-deco poster style, metallic effects, uniform-width strokes.

Closest of the free fonts tried (for orientation only): **Gloock** (contrast, blade-like serifs) and **Cinzel Decorative** (swashes growing from capitals); **Bodoni Moda Display** sits in the right weight class.

## 4. What the website needs from the font project

### 4.1 Files

| Deliverable | Required | Format and naming |
|---|---|---|
| Web font | **Yes** | `.woff2`, one file per style, e.g. `fabian-display-regular.woff2`. A variable font (`fabian-display[wght].woff2`) is welcome if there are weights. |
| Desktop/source export | Yes | `.otf` (or `.ttf`) of the same styles, so specimens and social images can use it. Keep the editor source file (`.glyphs`, `.ufo`, `.sfd`) **in the font project only** — this website repo is public. |
| Wordmark (R1) | Recommended | `wordmark-fabian-langer.svg` and `signoff-fabian.svg`: outlined paths (fills, no strokes), tight `viewBox`, no transforms, no embedded fonts, `fill="currentColor"`. If you also export the *centre lines* (stroke paths) I can animate them drawing themselves. |
| Specimen | Yes | One PNG/PDF showing all glyphs, the feature alternates, and the sample lines in §4.4. |
| Spec note | Yes | A short `README` with: family name, style names, which OpenType features exist (§4.3), cap height and x-height in font units, and the licence. |

### 4.2 Character set

- **Letters:** A–Z, a–z (both cases; R2 headings use mixed case).
- **Figures:** 0–9 (lining). Old-style figures optional.
- **Punctuation and symbols:** `. , : ; ! ? ' " ‘ ’ “ ” - – — ( ) & / + % # @ · …` and the euro sign `€`.
- **Accents** (names and Dutch/English words on the site, e.g. *Univé*): `é è ê ë á à ä â í ì ï î ó ò ö ô ú ù ü û ç ñ` in both cases.
- Space and non-breaking space with sensible widths.

### 4.3 OpenType features (tell me which you build)

| Feature | Use on the site |
|---|---|
| `kern` | Required. Kern at least the pairs in your name and common heading pairs (Fa, La, an, ng, er, Te, Yo, “W”, etc.). |
| `liga` | Standard ligatures, on by default. |
| `dlig` | Discretionary (swash) ligatures; I switch them on only for R1/R3. |
| `swsh` or `ss01`–`ss05` | Swash/alternate letters (e.g. a botanical F, L, g); I enable them per role in CSS. Name each set in the README. |
| `lnum` / `onum` | If both figure styles exist. |

### 4.4 Metrics and test lines

- **Units per em 1000.** Set ascender/descender (hhea, typo and win metrics) so swashes are **not clipped** at line-height 1.1–1.2; note in the README if swashes intentionally reach outside.
- Report **cap height** and **x-height**; I use them to size the fallback font so the page does not jump while the font loads.
- Test these real lines from the site at 40, 72 and 120 px:
  - Fabian Langer · FABIAN LANGER · Fabian
  - From strategy to solutions.
  - What do we mean by self-learning?
  - Not everything that adapts, learns.
  - Confusing concepts make for crippling policy.
  - Services · Recent work · Talks & workshops · The full story behind my posts
  - 9+ · 6+ · 302+ · 01 02 03 04

### 4.5 Licence

Your own font: any licence you like. Note that web fonts are downloadable by visitors by nature. If you are fine with reuse, the SIL Open Font License is the simplest; otherwise "All rights reserved, licensed to fabianlanger.nl".

## 5. How it goes into the site

1. Put the `.woff2` files in `app/fonts/` of this repo.
2. Load them with `next/font/local` in `app/layout.tsx`, replacing (or next to) the script font:

```ts
import localFont from "next/font/local"

const display = localFont({
  src: [{ path: "./fonts/fabian-display-regular.woff2", weight: "400", style: "normal" }],
  variable: "--font-display",
  display: "swap",
  adjustFontFallback: "Times New Roman", // keeps layout stable while loading
})
```

3. Add a `.font-display` class in `app/fl.css` and apply it per role (R1–R4) to the components (`components/home/home-page.tsx`, `components/article/article-header.tsx`, `components/article/article-ending.tsx`, `components/writing/writing-browser.tsx`, `components/site/*`).
4. Turn on features per role with `font-feature-settings` (e.g. `"dlig" 1, "ss01" 1` for the wordmark only).
5. Check: gradient highlight on display words, line-height without clipping, mobile sizes, and the article title wrapping.

## 6. Then: the style guide (second deliverable)

Icons, ornaments, frames, dividers and the route vine on the site are **vector drawings (SVG) generated in code**. Today they are drawn from centre lines and, in the latest prototype, given contrast by a simulated broad-nib pen (`components/fl/nib.tsx`: pen angle, minimum and maximum width, tapering ends). If the style guide expresses the font's logic as **rules and numbers**, I can apply it to every icon and ornament consistently.

Please include:

| Topic | What I need |
|---|---|
| **Stroke model** | Is it a broad nib (give the **pen angle**), a pointed pen (pressure-based), or drawn shapes? **Contrast ratio** thin : thick (e.g. 1 : 8). How thick strokes relate to the icon size. |
| **Terminals** | The vocabulary of stroke endings with proportions: ball (radius vs. stem), teardrop, blade/leaf (length, where the swell sits), flat cut. When to use which. |
| **Joins and curves** | How a straight stroke turns into a curve (sudden or gradual), where hairlines join heavy strokes, curve tension. |
| **Asymmetry** | Where the weight sits in a swell (e.g. "peak at 35% of the stroke"), as in the 3A corner leaf. |
| **Construction** | Icon grid (today 48 × 48), safe area, optical size: how the rules change from 24 px icons to 600 px diagrams. |
| **Ornament kit** | The base pieces drawn in the style: corner (start from 3A), divider, frame/arch, vine segment, a few terminals. |
| **Do / don't** | With examples, like §3. |
| **Colour** | Unchanged unless you decide otherwise: flat IBS yellow `#F9C852` for lines; red only as the end of a yellow→red gradient (`#F9C852 → #F08A3C → #C8302A`); dark background `#171717`; relief only on the single focal element. |

**SVG format for guide examples:** each piece as two files — the **centre line** (`*-line.svg`, strokes, for drawing animations) and the **outlined result** (`*-outline.svg`, fills). `viewBox` on a clear grid, no transforms, no groups with styles, colours as `currentColor`.

## 7. Context and decisions so far

- Site and code: see `README.md`. Design history (rounds 1–6): branch `prototype/website-design` and the throwaway route `/prototype/floral` (round 6: high-contrast fonts, broad-nib icons).
- **Decided:** photo frames = straight double frame with the restrained botanical corner on the diagonal (**3A**). The "From strategy to solutions" route becomes a **vine**. Icons: closest is the **tapered broad-nib stroke inside a light arch (C)** — "close, but not fully"; the font's style guide should settle it.
- **Still open, not part of this project:** real yearly rates for the self-updating stats (professionals trained, events spoken).
