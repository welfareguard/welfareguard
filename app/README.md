# WelfareGuard app

The public, plain-language face of WelfareGuard: a single-page React app where
anyone can run the compiled guard on their own text, watch the 768 real agent
runs one at a time, read the results as charts, browse the fifteen scenarios
and look up what the words mean. It is the same data as the static bench in
`docs/bench/`, presented for people who have never heard of an eval.

Stack: Vite 5, React 18, TypeScript, Tailwind CSS 3, react-router, recharts,
lucide-react. This is the stack Lovable generates, so the folder drops into a
Lovable project unchanged.

## Pages

| Route | What a visitor does there |
| --- | --- |
| `/` | The question, five-step walkthrough, headline numbers, a ten-second demo of the false alarm |
| `/try` | Types any message; the real Tier-1 guard decides, with matches highlighted and a false-alarm check on the fifteen harmless twins |
| `/replay` | Picks one of 768 runs; sees the job, what was slipped in, every tool call, the final message and the verdict in plain words |
| `/results` | Failures per model, what the agents did per kind of harm, the per-trap grid, and the guard's report card |
| `/scenarios` | The fifteen traps and their harmless twins, with details on demand |
| `/learn` | Two-minute explainer, glossary, FAQ, what this is not |

The data is `public/data.json`, copied from `docs/bench/data.json`. Refresh it
after every new eval run (see `docs/bench/README.md`).

## Run locally

```
cd app
npm install
npm run dev        # http://localhost:8080
npm run build      # type-check + production build into dist/
```

## Open it in Lovable

Lovable creates and owns the GitHub repository for a project, so the app is
moved into that repository rather than imported from this one:

1. In Lovable, create a new blank project and connect it to GitHub
   (Settings → GitHub → Create repository). Lovable pushes its template.
2. Clone that repository, delete everything in it except `.git`, and copy the
   contents of this `app/` folder into its root (`package.json` and
   `vite.config.ts` must be at the root).
3. Commit and push. Lovable picks the push up, builds it, and from then on edits
   it in place; the "Publish" button gives it a public URL.

A one-liner for step 2, run inside the clone:

```
git rm -rq . && npx degit welfareguard/welfareguard/app . && git add -A && git commit -m "Import WelfareGuard app"
```

Any other static host works too: `npm run build` and serve `dist/` with a
single-page-app fallback to `index.html` (Vercel, Netlify and Cloudflare Pages
do this by default).

## Notes

- The build uses `@vitejs/plugin-react` (Babel) rather than the SWC plugin so
  it also builds on machines whose application-control policy blocks native
  Node add-ons. Lovable accepts either.
- Theme follows the system and can be toggled; the choice is kept in
  `localStorage` only.
- No analytics, no network calls other than fetching `data.json` and the two
  Google Fonts families.
