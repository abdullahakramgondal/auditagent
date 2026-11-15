# AuditAgent AI: front end

A web screen for the AuditAgent AI backend. Upload a contract, a purchase order and an invoice;
the backend reads them and says whether the vendor billed the right amount. The front end only
uploads, waits and shows: all the reading and all the money maths are done by the backend.
Synthetic or test documents only. Version 1: PKR only, no login, English only.

## Stack

React 19, TypeScript (strict), Vite, Tailwind CSS 4, React Router, TanStack Query (polling and
caching), Zod (checks every answer of the backend), decimal.js (money is text, never a JS number),
Vitest and Testing Library.

## Run it for development

Two terminals. From the project root, with the Python virtual environment on:

```
uvicorn auditagent.api.app:create_app --factory --reload
```

From this folder:

```
npm install
npm run dev
```

Open http://localhost:5173. The API address is `VITE_API_BASE_URL` (see `.env.example`).

## Run it as one server (demo, deployment)

```
npm run build
cd ..
uvicorn auditagent.api.web:create_web_app --factory
```

Open http://127.0.0.1:8000. The backend serves the built front end at `/` and keeps its API under
`/api` (the API docs are at `/api/docs`). The production build gets `VITE_API_BASE_URL=/api` from
`.env.production`. Node is needed only to build.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | development server with hot reload |
| `npm run build` | type check and production build into `dist/` |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript |
| `npm test` | all unit and component tests |

A change is done only when `lint`, `typecheck` and `test` pass.

## Folder map

```
src/
  app/        AppShell (header, nav, notice), providers
  pages/      one file per route; they only compose features
  features/
    upload/   the three drop zones, file checks, starting an audit
    audit/    progress, failed state, result, findings, extracted documents
    history/  the list of audits
  api/        fetch wrapper, ApiError, one function per endpoint, Zod schemas, query keys
  shared/     status look (statusMeta), money and date helpers, small UI parts
  mocks/      fixtures with real results (also used by the tests)
  test/       fake fetch and query wrapper for tests
```

Rules: a page imports a feature only through its `index.ts`; a feature never imports another
feature; components never call `fetch` (hooks do); `api/` imports nothing from the app.

## Rules of the screens

- A result of NEEDS_REVIEW is a normal result with an amber banner, never an error screen.
- Colour is never the only signal: a status always has an icon and text.
- Money comes as text and is printed only by `formatPkr`; dates only by `formatDate` and
  `formatDateTime`. Nothing is added or compared in the browser.
- Every finding shows the contract clause and its page.
- An answer of the backend that does not match its schema is never shown as a result.

## The API it uses

`POST /audits` (three PDFs), `GET /audits` (history), `GET /audits/{id}` (state),
`GET /audits/{id}/result`, `GET /audits/{id}/result.json` (download). The shapes are in
`src/api/schemas.ts` and follow `src/auditagent/api/schemas.py` of the backend.
The backend gives no step of the work, only queued, running, done or failed.