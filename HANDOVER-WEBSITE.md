# Handover: Nebuloria for fabianlanger.nl

The answer to `FONT-HANDOVER.md` (written from the website repo). It covers what was delivered, how to put it in the site, what is still missing, and which design rules the site can adopt.
Version 1.5, 2026-11-07. Font family **Nebuloria** with two styles, **Regular** and **Hekwerk**. Licence: SIL OFL 1.1 (free, may be public).

---

## 1. Delivered files

| What | Path in this repo | For the site |
|---|---|---|
| Web font, Regular | `dist/nebuloria-regular.woff2` | → `app/fonts/` |
| Web font, Hekwerk | `dist/nebuloria-hekwerk-regular.woff2` | → `app/fonts/` (only if the fence is used) |
| Desktop fonts | `dist/nebuloria-regular.otf`, `dist/nebuloria-hekwerk-regular.otf` | specimens, social images |
| Wordmark (R1) | `dist/svg/wordmark-fabian-langer.svg` | hero, if an SVG is preferred over live text |
| Sign-off | `dist/svg/signoff-fabian.svg` | under every article |
| Design book | `docs/Nebuloria-Design-Book.pdf` | story and inspiration |
| Style guide | `docs/Nebuloria-Style-Guide.pdf` | rules for icons, ornaments, colour and type |
| Components | `docs/style-guide/svg/*.svg` | window, wire, reference letters S G E, leaf in the a |

SVGs follow §4.1: filled outlines, tight `viewBox`, no transforms, no embedded fonts, `fill="currentColor"`. **Centre lines (stroke paths) are not available**: the letters were traced as outlines. A draw-on animation needs separately drawn centre lines (see §6).

## 2. Spec note (§4.1 README)

| Item | Value |
|---|---|
| Family / styles | Nebuloria · Regular, Hekwerk (typographic family "Nebuloria") |
| Units per em | 1000 |
| Cap height / x-height | **700 / 500** |
| Ascender / descender (hhea, typo, win) | 904 / −339 (generous: tendrils and descenders are never clipped) |
| OpenType features | `dlig`, `ss01` (no `kern`, `liga`, `swsh` or figures yet; see §4) |

| Feature | Regular | Hekwerk |
|---|---|---|
| `dlig` | Wires (Fa La ng er re ce ge) + at most **one window per word** | Wires + a **window in every pair** of stems |
| `ss01` | Window in every pair (the fence) | Back to one window per word |

Window classes: right-stem letters `a d h i l m n u` followed by left-stem letters `b h i k l m n p r u`.

## 3. Putting it in the site

```ts
// app/layout.tsx
import localFont from "next/font/local"

export const display = localFont({
  src: [{ path: "./fonts/nebuloria-regular.woff2", weight: "400", style: "normal" }],
  variable: "--font-display",
  display: "swap",
  adjustFontFallback: "Times New Roman",
})

// optional, only where the iron fence is wanted
export const displayFence = localFont({
  src: [{ path: "./fonts/nebuloria-hekwerk-regular.woff2", weight: "400", style: "normal" }],
  variable: "--font-display-fence",
  display: "swap",
})
```

```css
/* app/fl.css */
.font-display { font-family: var(--font-display), "Times New Roman", serif; font-weight: 400; }

.role-wordmark { font-size: clamp(80px, 11vw, 160px); line-height: 1.1; font-feature-settings: "dlig" 1; }  /* R1 */
.role-heading  { font-size: clamp(36px, 6vw, 96px);  line-height: 1.15; }                                /* R2 */
.role-heading.is-large { font-feature-settings: "dlig" 1; }                                              /* R2 at 72 px+ */
.role-quote    { font-size: clamp(30px, 4vw, 60px);  line-height: 1.2; font-feature-settings: "dlig" 1; } /* R3 */

/* the moving gradient highlight works as before */
.highlight { background: linear-gradient(100deg, #F9C852, #F08A3C 60%, #C8302A);
             -webkit-background-clip: text; background-clip: text; color: transparent; }
```

Notes:

- Tendrils and descenders reach outside the line box at line-height 1.1–1.2. They are **not clipped**, but keep `overflow: visible` on heading containers.
- The hairlines (≈ 13/1000 em) stay visible under the gradient from ~40 px. Below 40 px use Poppins.
- For the hero, live text with `dlig` and the SVG wordmark look the same. Live text is selectable and indexable; the SVG is pixel-stable. With the SVG, add `role="img" aria-label="Fabian Langer"`.

## 4. Not done yet (the next font version)

The handover's character set (§4.2) is only partly covered. v1.5 has **A–Z, a–z, space, non-breaking space**.

| Missing | Effect on the site now | Workaround until v1.6 |
|---|---|---|
| Figures 0–9, `+` (R4) | Stats would fall back to Times | Keep R4 in Poppins |
| Punctuation `. , : ; ! ? ' " ‘ ’ “ ” - – — ( ) & / % # @ · … €` | e.g. the `?` in "What do we mean by self-learning?" falls back | Wrap punctuation in a Poppins span, or rephrase titles |
| Accents `é è ê ë á à ä â í ì ï î ó ò ö ô ú ù ü û ç ñ` | "Univé" falls back on the `é` | Avoid in display text for now |
| `kern` | No pair kerning; a few pairs (La, Te, th) are loose or tight | Acceptable at display sizes; tune per heading with `letter-spacing` if needed |

Test lines from §4.4 that work fully today: *Fabian Langer · FABIAN LANGER · Fabian · From strategy to solutions · Not everything that adapts learns · Services · Recent work*.

## 5. What the design means for the rest of the site

The style guide turns the font's logic into rules for the site's SVG drawings (§6 of `FONT-HANDOVER.md`). In short:

| Topic | Rule from Nebuloria | For `components/fl/nib.tsx` and the ornaments |
|---|---|---|
| Stroke model | **Broad nib at 45°**, contrast ≈ **8 : 1** | `penAngle: 45`, `maxWidth = stem`, `minWidth = stem / 8` (≥ 1 px) |
| Stem in icons | 48 px grid: 5 px stem, 1 px hairline | contrast drops to ≈ 5 : 1 at 48 px, ≈ 2.5 : 1 at 24 px |
| Taper | Full weight for 80% of a stroke, then a needle point | taper the last 20% |
| Tendril | Hairline ≈ stem ÷ 10, swelling into a teardrop (≈ 3 × its width) | for the route vine and decorative lines |
| Corners | 45° chamfers, never perfect circles | frames, cards, the arch around icons |
| Direction | Diagonals and curls only NE → SW | ornament curls |
| Ornament | Grows from the stroke; leaves only inside closed shapes | "botanical, not floral" stays |
| Components | Window (hairline frame, 45° glare lines) and wire (hanging liana) | window as a frame or callout; wire to connect route steps |

**Decisions for you (not made by this project):** the site already decided on the botanical corner "3A" for photo frames and a broad-nib icon in a light arch "C". Nebuloria fits both. The chamfered **window** is an alternative frame worth trying for one highlighted photo or card. The **wire** is a natural candidate for the "From strategy to solutions" route vine.

## 6. Possible follow-ups

1. Font v1.6: figures, punctuation, accents and `kern` (same pipeline: draw sheets → `scripts/prepare_glyphs.py` → `scripts/build_font.py`).
2. Centre-line SVGs for the wordmark and sign-off (for a draw-on animation).
3. An ornament kit in the style (corner, divider, arch, vine segment) as `*-line.svg` + `*-outline.svg` pairs, following the style guide.
