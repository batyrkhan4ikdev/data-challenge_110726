# Embedding the CQA UI in Dynamics 365 as an HTML web resource (R4, #33)

Question: can `web/` (plain ES modules, `mountCqa(root, {apiBase})`, styles under `.cqa`) run inside a Dynamics 365 / model-driven app as an HTML web resource, and what has to change? Sources are Microsoft Learn (checked 2026-11-07) and MDN. Claims marked **[INFERENCE]** are not stated by a source and need a check in a real environment.

## Constraints

| Topic | What the platform does | Effect on this repo |
|---|---|---|
| File types and size | Web resources are virtual files stored in Dataverse: `.htm/.html`, `.css`, `.js`, `.png/.jpg/.gif/.svg/.ico`, `.xml/.xsl`, `.resx`. The upload limit is `Organization.MaxUploadFileSize`, **5 MB by default** ([web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/web-resources)). | The packager checks each resource is smaller than 5,000,000 bytes and rejects other extensions, including source maps and font files. |
| Names | A name "can only include letters, numbers, periods, and nonconsecutive forward slash" characters, and the publisher prefix is prepended ([create/edit web resources](https://learn.microsoft.com/en-us/power-apps/maker/model-driven-apps/create-edit-web-resources)). | Modules use `appealModal`, `criteriaTable`, `checklistEditor`; logos use `logoCqaLight.svg` and `logoCqaDark.svg`. The validator applies `^[A-Za-z0-9.]+(/[A-Za-z0-9.]+)*$` **after** `cqa_/`. The publisher prefix contains `_`, as in Microsoft's example `new_/test/test.htm`; it is not part of the validated name. |
| Links between files | Use relative URLs between web resources, and simulate folders with `/` in names. Don't use `/WebResources/...` as a root path ([web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/web-resources), [HTML web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/webpage-html-web-resources)). | Our imports are already relative (`./views/…`, `../ui/…`). Upload them as `cqa_/dist/main.js` and so on. **Untested:** the MS docs mention neither ES modules nor the MIME type used for `.js` web resources, and `type="module"` requires a JavaScript MIME type ([MDN](https://developer.mozilla.org/docs/Web/HTML/Reference/Elements/script/type)). The safe alternative is one bundled `.js` and one `.css`. |
| Hosting on a form | An HTML web resource on a form is an IFRAME. The form runtime **may destroy and re-create it**, for example on tab switches, so initialization must be idempotent ([HTML web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/webpage-html-web-resources), [getContentWindow](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/clientapi/reference/controls/getcontentwindow)). It can also open as a full page or dialog with `Xrm.Navigation.navigateTo({pageType: "webresource", webresourceName, data})` ([navigateTo](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/clientapi/reference/xrm-navigation/navigateto)). | `mountCqa` replaces the root's children and returns an unmount function, so re-mounting is safe. Hash routing (`#/…`) lives inside the IFRAME. |
| Query parameters | Only `typename, type, id, orgname, userlcid, orglcid, data, formid` (plus internal ones) are accepted; «the web resource will not open if other parameters are used». Custom configuration goes into `data` ([HTML web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/webpage-html-web-resources), [form properties](https://learn.microsoft.com/en-us/power-apps/maker/model-driven-apps/web-resource-properties-legacy)). | `apiBase` (and the group or conversation id) must arrive in `data`, not as our own query parameters. |
| Access to `Xrm` | A web resource on a form may use `parent.Xrm.Page` / `parent.Xrm.Utility`, but not globals defined by form scripts. It should load its own libraries ([HTML web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/webpage-html-web-resources)). | We need no `Xrm` to work. The optional record context comes from the `id`/`typename` parameters. |
| Sandbox | «Restrict cross-frame scripting» sets `sandbox=""`, which applies all restrictions and can stop scripts from running ([IFRAME and web resource controls](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/use-iframe-and-web-resource-controls-on-a-form)). | The option must stay **off** for our control. |
| CSP | Default CSP when enforced: `script-src * 'unsafe-inline' 'unsafe-eval' blob:; style-src * 'unsafe-inline' blob:; …; frame-ancestors 'self' https://*.powerapps.com`. **Strict CSP** sets `default-src 'self'` and `connect-src 'self' blob: data: wss: <platform>`, with `connect-src` customizable per environment ([Power Platform CSP](https://learn.microsoft.com/en-us/power-platform/admin/content-security-policy)). | Enforcement is a per-environment admin toggle, and Microsoft advises enabling it on dev/test first. That suggests it's off unless an admin turns it on **[INFERENCE]**. The default CSP is fine: no `eval`, `innerHTML` or inline script in `web/src`. Under Strict CSP an admin must add our API origin to `connect-src`. **[INFERENCE]** Call audio falls back to `default-src 'self'` because no `media-src` is listed ([MDN default-src](https://developer.mozilla.org/docs/Web/HTTP/Headers/Content-Security-Policy/default-src)), so it would be blocked unless served from an allowed origin. |
| Calling our API | The page origin is the Dynamics org, so calls to the CQA API are cross-origin. `fetch` with `Content-Type: application/json` triggers a CORS preflight ([MDN CORS](https://developer.mozilla.org/docs/Web/HTTP/Guides/CORS)). An HTTPS page can't fetch `http://` ([MDN mixed content](https://developer.mozilla.org/docs/Web/Security/Mixed_content)). Litestar enables CORS with `Litestar(cors_config=CORSConfig(allow_origins=[…]))` ([Litestar middleware](https://docs.litestar.dev/latest/usage/middleware/builtin-middleware.html)). | `CQA_ALLOWED_ORIGINS` enables CORS for the comma-separated origins, GET/POST/PUT and Content-Type. Empty or unset leaves `cors_config=None`, preserving standalone behavior. Production still needs an HTTPS API. |
| Recommended path | Microsoft suggests PCF components or custom pages for «configurable, reusable, and tighter external integrations» ([web resources](https://learn.microsoft.com/en-us/power-apps/developer/model-driven-apps/web-resources)). | A web resource is the lightest option and needs no build-tool change; PCF would be a rewrite. |

## Implemented for #40

`web/d365/index.htm` uses its own `cqa-d365` root. Its external `loader.js` reads `data` as JSON with `apiBase` and optional `route`, and forwards `id`/`typename` as record context. It shows Russian error banners for invalid configuration and failed module imports. Bootstrap messages are independent of the UI module so they remain available when that module cannot load. A static fallback also remains visible if the loader itself is blocked.

The loader uses relative imports and URLs. It needs no inline script, inline event handler, `unsafe-inline` script permission or `eval`. The external `cqa_/loader.js` was chosen instead of relying on the more permissive default D365 policy. It sets the initial hash before mounting to avoid a queued `hashchange` duplicating the initial request. `pagehide` calls the returned unmount function; a persisted `pageshow` mounts again after back/forward-cache restoration. A CSP violation in `connect-src`, `font-src` or `media-src` produces one hint naming the directive and blocked origin.

`scripts/package_d365.py` copies the loader, scoped stylesheet, compiled modules and assets into `out/d365/cqa_/`. It checks compiled output against every source and `tsconfig.json`, rejects stale/extra modules, invalid names/types, maps/fonts, oversized files, unscoped CSS selectors and root-absolute `url(...)` or `/static/` references. The standalone HTML and `standalone.css` are not shipped. Relative names must be preserved when uploading.

`server/app.py` only adds `CORSConfig`; it does not change routes or scoring. `tests/test_cors.py` covers GET/POST/PUT preflights, foreign origins, response headers and empty/unset origin lists. The form control must have "Restrict cross-frame scripting" OFF and "Pass record object-type code and unique identifier" ON.

## Local rig and reproducible commands

`scripts/d365_harness/serve_package.py` serves `out/d365` and a host iframe without `sandbox`. Policy selection is a server CLI argument, never a value inside `data`. Every `cqa_/*` response carries an HTTP `Content-Security-Policy` header; there is no CSP meta tag. JavaScript, HTML and SVG use `text/javascript`, `text/html` and `image/svg+xml`.

Profiles:

- `default`: the R4 permissive script/style policy, wildcard resource origins and `frame-ancestors 'self' http://127.0.0.1:8807`.
- `strict-no-api`: `default-src 'self'; connect-src 'self'; font-src 'self'; media-src 'self'; frame-ancestors http://127.0.0.1:8807`.
- `strict-api`: `default-src 'self'; connect-src 'self' http://127.0.0.1:8806; font-src 'self' data:; media-src 'self' http://127.0.0.1:8806; frame-ancestors http://127.0.0.1:8807`.

The server's optional `--media-origin` adds the signed audio link's origin to `media-src` in `strict-api`; its default is empty. The automated runner reads the call record from the local API, extracts only its audio origin, and passes that as a server CLI argument. An explicit runner `--media-origin` overrides discovery. This is server configuration, not iframe `data`. The tested origin was `https://ec88f21f1accecf38e20095a9fe175.a5.environment.api.powerplatform.com`. No signed query string is needed in the policy.

Commands from the isolated worktree on this Windows machine, using the main checkout's existing compiler, Python environment and throwaway API launcher:

```bash
C:/Users/sydyk/Downloads/data_challenge/web/node_modules/.bin/tsc -p web
C:/Users/sydyk/Downloads/data_challenge/web/node_modules/.bin/tsc -p web --noEmit
C:/Users/sydyk/Downloads/data_challenge/.venv/Scripts/python.exe -m pytest -q
C:/Users/sydyk/Downloads/data_challenge/.venv/Scripts/python.exe scripts/package_d365.py
C:/Users/sydyk/Downloads/data_challenge/.venv/Scripts/python.exe scripts/d365_harness/check_package.py

# Copy the store before any POST. Never point this scenario at the shared store.
cp -r C:/Users/sydyk/Downloads/data_challenge/data/store C:/Users/sydyk/AppData/Local/Temp/cqa-d365-fo_soqh0/store
CQA_ALLOWED_ORIGINS=http://127.0.0.1:8807 C:/Users/sydyk/Downloads/data_challenge/.venv/Scripts/python.exe C:/Users/sydyk/Downloads/data_challenge/tmp_work/serve.py 8806 --root C:/Users/sydyk/.omp/wt/tcdb6b709e/m --store C:/Users/sydyk/AppData/Local/Temp/cqa-d365-fo_soqh0/store

# Starts/stops :8807 for each profile and :8808 for the foreign-ancestor checks.
node scripts/d365_harness/run_checks.cjs --python C:/Users/sydyk/Downloads/data_challenge/.venv/Scripts/python.exe --out C:/Users/sydyk/AppData/Local/Temp/cqa-d365-fo_soqh0/shots --post

# Manual inspection of one profile, without the automated runner:
python scripts/d365_harness/serve_package.py --profile strict-api --port 8807
# Open http://127.0.0.1:8807/host.html

# Stop the CORS-enabled API before checking standalone behavior on the same port:
CQA_ALLOWED_ORIGINS= C:/Users/sydyk/Downloads/data_challenge/.venv/Scripts/python.exe C:/Users/sydyk/Downloads/data_challenge/tmp_work/serve.py 8806 --root C:/Users/sydyk/.omp/wt/tcdb6b709e/m --store C:/Users/sydyk/AppData/Local/Temp/cqa-d365-fo_soqh0/store
node C:/Users/sydyk/Downloads/data_challenge/tmp_work/shoot.cjs "" 1440 900 C:/Users/sydyk/AppData/Local/Temp/cqa-d365-fo_soqh0/shots/standalone.noCors.root.1440.png --base http://127.0.0.1:8806
```

The Playwright require path follows `tmp_work/shoot.cjs` on this machine. On another machine, point it at an installed Playwright package. The runner captures screenshots outside the repository and writes detailed `results.json`. It checks all seven routes at 1440, 1024 and 390 pixels, actual response CSP headers and MIME, cross-origin responses or blocked attempts, exact violation URL/directive sets, console errors, logo/font loading, and iframe scroll width. It recreates the iframe three times, compares request URLs per mount, and instruments `addEventListener`/`removeEventListener` to check one router listener while mounted and zero after `pagehide`. `--post` submits an appeal through the iframe and finds its comment in `#/review`.

## Evidence from the isolated slice, 2026-11-08

- TypeScript build and `--noEmit` both exited 0.
- `python -m pytest -q`: **151 passed in 5.29s**. The CORS regression tests first failed for missing allow-origin headers, then all seven passed after the CORS addition. Before the full suite, an explicit import/path assertion printed `C:\Users\sydyk\.omp\wt\tcdb6b709e\m\server\app.py` and confirmed it was inside the current worktree, not the main checkout's editable install.
- Package build: **22 resources, 150,573 bytes**. `check_package.py` ran 15 checks against temporary copies. Thirteen invalid cases exited 1 with an explanation; the valid copy and restored stylesheet exited 0. The required `dist/bad-name.js` case failed with `Invalid web resource name after cqa_/: dist/bad-name.js`.
- Rig: **64 passed, 8 failed**. The eight failures below belong to the pre-integration screen baseline, not the loader or CORS. They remain acceptance failures until the integrated tree is re-run. The runner deliberately exits nonzero; it does not suppress them.
- Both strict profiles rejected embedding from `http://127.0.0.1:8808`. Chromium reported `frame-ancestors http://127.0.0.1:8807`; the CQA frame did not load. The runner checked the HTTP policy header as well as the browser refusal.
- All three profiles passed iframe recreation three times. The initial mount and each of three replacements made exactly two requests, `/api/profiles` and `/api/checklists`. Each had one `hashchange` listener; dispatching `pagehide` removed it, leaving zero. This proves the cleanup handler and stable per-document mounts, not a long-duration memory profile or D365's lifecycle.
- Invalid JSON, missing `apiBase` and failed module import each displayed the Russian banner. An appeal was created through the iframe on the copied store, then its unique comment appeared in `#/review`; the scenario had no console or CSP errors.
- Passing default/strict-api route cases had no CSP/CORS errors, loaded logos and successful cross-origin API responses. Strict-no-api cases had only `connect-src` violations for exactly the attempted API URLs and displayed the origin/directive hint. There are no web fonts in this build, so `document.fonts` was empty.
- All 1024px iframe measurements were 1024; all 1440px measurements were 1440. At 390px, the exceptions are listed below. Other routes measured 390. Analytics strict-api's failure is CSP, not width.
- The plain `/` page on :8806 with CORS disabled measured `scrollWidth=1440`, `overflow=false`, `problems=[]`. A GET with an Origin header returned 200 and no `access-control-*` headers.
- Computed WCAG contrast: loader error text `#8A1C13` on `#FDECE9` **8.13:1**; rig text `#323335` on white **12.65:1**, on `#F5F6F7` **11.69:1**.

Pending integration failures:

| Runner case | Observed failure |
|---|---|
| `default 390 #/dialogs/DEV` | scrollWidth 500 instead of 390 |
| `default 390 #/checklists` | scrollWidth 439 instead of 390 |
| `strict-no-api 390 #/dialogs/DEV` | scrollWidth 423 instead of 390 |
| `strict-api 1440 #/analytics/DEV` | 11 `style-src-attr` violations from baseline inline style attributes |
| `strict-api 1024 #/analytics/DEV` | Same `style-src-attr` violations |
| `strict-api 390 #/dialogs/DEV` | scrollWidth 500 instead of 390 |
| `strict-api 390 #/checklists` | scrollWidth 439 instead of 390 |
| `strict-api 390 #/analytics/DEV` | Same `style-src-attr` violations |

The list-screen owner is fixing the width failures; the integrator has a CSSOM style-assignment fix for the analytics violations. Neither patch was present in this isolated slice. Rebuild and rerun the commands above from the integrated checkout, changing the API launcher's `--root` to that checkout. A green integrated run is still required.

Screenshots and detailed evidence are outside the repository at `C:/Users/sydyk/AppData/Local/Temp/cqa-d365-fo_soqh0/shots/`: `results.json`, `{default,strict-no-api,strict-api}.{0..6}.{1440,390}.png`, `invalid.data.390.png`, `missing.data.390.png`, `appeal.review.1440.png`, and `standalone.noCors.root.1440.png`. Route indices follow the seven-route order in the runner.

## Deployment limits

- **[INFERENCE]** ES-module loading and JavaScript MIME in an actual D365 organization remain untested. The local rig sends the required MIME explicitly; it cannot establish what Dataverse sends.
- **[INFERENCE]** The tenant must allow the HTTPS API origin in `connect-src`, and the API must allow the exact organization origin through `CQA_ALLOWED_ORIGINS`. This rig uses HTTP loopback and proves neither TLS deployment nor tenant configuration.
- **[INFERENCE]** `font-src 'self' data:` is configured in the strict-api profile, but embedded fonts in a real strict-CSP tenant remain untested. The UI embeds an Onest woff2 subset as a base64 `data:` URL in `web/cqa.css` (about 45 KB of CSS), so a strict tenant CSP must allow `data:` in `font-src`.
- **[INFERENCE]** `audio_url` is a signed Dynamics link. Strict CSP needs `media-src` for that link's origin. The local fixture has no audio file and cannot prove playback, seeking or signed-link expiry handling under strict CSP. A proxy `GET /api/conversations/{cid}/audio` is the proposed fix, tracked in #39/#40; this change does not implement it.
- A real organization still needs an upload/form smoke test, including record parameters, tab recreation and the tenant's CSP. No D365 trial was registered.

Готово к загрузке как HTML web resource, проверено на локальном стенде, условия перечислены. This is not a claim of operation inside Dynamics 365.
