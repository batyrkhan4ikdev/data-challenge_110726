# Redesign brief: Freedom-style UI for the CQA web app

Status: research input for independent design proposals. Nothing in `web/` has changed yet.

## Goal

Improve the look and usability of `web/` (CQA: Conversation Quality Analytics for Freedom Broker) so it reads as a Freedom product: the visual language of Freedom Broker / Freedom Bank, applied to an internal QA tool for a large corporate customer.

## Hard constraints

1. **Architecture stays.** Plain TypeScript ES modules, no framework, no bundler, `tsc` build (`npm run build --prefix web` → `web/dist`). Every style rule is scoped under the root class `.cqa`; the entry point is `mountCqa(root, {apiBase})` (`web/src/main.ts`). It has to embed as a Dynamics 365 HTML web resource (`docs/research/d365-web-resources.md`).
2. **D365 file types.** Web resources accept `.htm/.html .css .js .png .jpg .gif .svg .ico .xml .xsl .resx`. Font files (`.woff2`, `.ttf`) are **not** on the list. A custom font therefore has to be a system font, a `data:` URI inside the CSS (the 5 MB per-file limit applies), or an external CDN, which may be blocked by Strict CSP (`font-src`/`style-src`).
3. **Audience (organizer #3011).** A large corporate customer: executives, QA specialists, employees. Avoid cartoonish or playful styling.
4. **Demo-critical elements (organizer mockup #3015, `docs/demo.md`).** Sidebar Диалоги / Чек-листы / Апелляции / Аналитика, the score ring, per-criterion points `x / weight`, «Почему снижена оценка», «Перейти к фрагменту», «Оспорить оценку», gross-error filter, audio seek on evidence click, appeal → review → recomputed total, checklist edit → new version → «Переоценить». Restyle them; don't remove them.
5. **Deadline.** The stop-code tag is at 12:00 on 8 Nov 2026 (issue #29), and the demo runs on the live UI. The change list must be ordered so that stopping after any item leaves a coherent UI.
6. **Accessibility.** WCAG 2.2 AA: 4.5:1 for body text, 3:1 for large text and UI components, visible focus, `prefers-reduced-motion`, keyboard operability. These rules already exist in `web/cqa.css` and must not regress.
7. **Content.** Transcripts are RU / KZ / EN (Kazakh Cyrillic: ә ғ қ ң ө ұ ү һ і). UI strings are Russian and live in `web/src/i18n.ts`.
8. **Mode.** In impeccable terms this is an *Operate* surface: scanability, consistency and density come before expression. The brand shows in precise details, not in marketing heroes.

## Freedom reference (measured 2026-11-07)

Files are in `docs/redesign/reference/`: `freedom-broker*.png`, `freedom-bank*.png`, `freedom-holding.png`, and `computed-styles.json` (computed styles, colour frequencies, gradients, radii, shadows, CTA styles).

| Site | Font | Text / muted | Backgrounds | Accent | Shape |
|---|---|---|---|---|---|
| Freedom Broker (`fbroker.kz`; `ffin.kz` redirects there) | `"CoFo Sans"` (body 18px; headings 900, 60–84px) | `#323335` / `#6A788A` | `#FFFFFF`, tint `#F3F8FF`, success tint `#DFF5EC`, borders `#B2BCC8` | brand gradient `linear-gradient(91deg, #7D8DEE -1.79%, #1CCC9E 25.51%, #1AE276 82.98%)` on the primary CTA (dark text `#323335`, 18px/500, padding 16px 52px) and on headline text; greens `#00B323 #009753 #13AD64 #4FB446`; red `#EE5555` | radii 20 / 16 / 14 / 12 / 8px; card shadow `0 5px 15px rgba(0,0,0,.08)`; outline secondary button with a green border |
| Freedom Bank (`bankffin.kz`) | `CoFoSans` (body 14px, h1 40px/500) | `#191919` / `#5C5C5C` | page `#F5F6F7`, white cards with a 1px border, no shadows | `#2A8640`, `#78BB2F` | radii 10 / 6 / 16px |
| Freedom Holding | `"Museo Sans"` / Roboto | `#4D4D4F` | white | `#4FB84E` square buttons | 0px |

Measured WCAG contrast:

| Pair | Ratio |
|---|---|
| `#323335` on `#FFFFFF` | 12.65 |
| `#6A788A` on `#FFFFFF` | 4.50 |
| `#6A788A` on `#F3F8FF` | 4.22 (fails 4.5 for body text) |
| `#00B323` on `#FFFFFF` | 2.81 (fails as text) |
| `#009753` on `#FFFFFF` (and white on it) | 3.78 |
| `#2A8640` on `#FFFFFF` (and white on it) | 4.58 |
| `#007A43` on `#FFFFFF` | 5.43 |
| `#323335` on gradient stop `#7D8DEE` | 4.17 (fails 4.5 at the left edge) |
| `#323335` on gradient stop `#1CCC9E` | 6.13 |
| `#323335` on gradient stop `#1AE276` | 7.34 |
| white on `#1CCC9E` | 2.06 (fails) |
| `#EE5555` on `#FFFFFF` | 3.46 (fails as text) |

CoFo Sans is a commercial typeface from Contrast Foundry. We hold no licence for it, so the proposal must pick a licensed substitute that covers Kazakh Cyrillic, plus a delivery method that fits constraint 2.

## Current state

- Baseline screenshots, taken with fake-model data: `docs/redesign/baseline/<screen>.<desktop|mobile>.png` (desktop 1440×900 full page, mobile 390×844). Screens: `dialogs`, `result-chat`, `result-call`, `review`, `checklists`, `checklist-editor`, `analytics`. Older screenshots with real-model data are in `docs/screenshots/`.
- The previous visual pass was #25 (C6): a dark-green sidebar `#0f5132` after mockup #3015. Tokens are at the top of `web/cqa.css`: 1441 lines, 272 `.cqa` rules, media queries at 860 / 1000 / 1100px, and one reduced-motion block.
- Code: `web/src/main.ts` (shell, nav), `web/src/views/*.ts` (7 screens), `web/src/ui/*.ts` (dom helpers, icons, transcript, criteria table, appeal modal, facts). `web/src` uses about 178 distinct `cqa-*` class names.

## Running it

- A server with offline data runs at **http://127.0.0.1:8791** (`LLM_PROFILE=fake`; `data/store` holds 65 fake DEV evaluations). Port 8787 is taken by an unrelated process on this machine. To start your own server: `.venv/Scripts/python.exe -m uvicorn server.app:app --port <free port>` from the repo root.
- Routes: `#/dialogs/DEV`, `#/evaluation/p1-ru-001-132ab7e5` (chat), `#/evaluation/p4-ru-003-3c6c365a` (call), `#/review`, `#/checklists`, `#/checklists/chat`, `#/analytics/DEV`.
- Headless browser: Playwright via Node. Use `require('C:/Users/sydyk/AppData/Local/npm-cache/_npx/606f4d49f911e2b4/node_modules/playwright-core/index.js')`; Chromium headless shell 1254 is installed. `docs/redesign/capture.cjs` is a working example. The built-in browser tool's daemon fails on this machine.
- Fake-model explanations read «Тестовое обоснование», and call audio shows 0:00, because the fixture has no audio. Judge layout, not content.

## Installed design skills

Read each `SKILL.md` by path. The base is `C:/Users/sydyk/.agents/skills/` unless noted.

| Skill | Use it for |
|---|---|
| `C:/Users/sydyk/.agent/skills/ui-ux-pro-max` | Searchable style/colour/typography/UX database: `python <dir>/scripts/search.py "<query>" --design-system` or `--domain ux\|color\|typography\|chart` (use `.venv/Scripts/python.exe`) |
| `impeccable` | Design-director workflow: `reference/critique.md`, `audit.md`, `operate.md`, `mode-operate.md`, `colorize.md`, `typeset.md`, `layout.md`, `craft-floor.md`, `polish.md` |
| `refactoring-ui` | Hierarchy, spacing scale, colour and depth audit |
| `web-design-guidelines` | Vercel Web Interface Guidelines; fetch `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md` and check the files against it |
| `design-review` | Structured critique against a brief |
| `design-tokens` | Token file structure |
| `web-typography` | Type scale, font pairing, readability |
| `ux-heuristics` | Nielsen-style usability heuristics |
| `frontend-design` | Distinct, non-templated visual direction |
| `design-taste-frontend` | Anti-slop checks (written for marketing sites; use only the parts that fit an app UI) |
| `extract-design-system` | Already run on Freedom sites; its output is folded into `reference/computed-styles.json` |
