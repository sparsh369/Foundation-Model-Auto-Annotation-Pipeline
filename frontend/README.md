# Operator Console (frontend)

Next.js 14 (App Router) + TypeScript + TailwindCSS + React Query.

```bash
cp .env.example .env.local
npm install
npm run dev        # http://localhost:3000  (proxies /api → backend)
```

## Pages
- `/` — dashboard (dataset + image counts, recent datasets)
- `/datasets` — dataset management & image upload (presigned)
- `/jobs` — launch auto-annotation jobs with open-vocab prompts
- `/reviews` — human-in-the-loop review queue (approve / reject / correct)
- `/analytics` — confidence distribution & model monitoring
- `/admin` — audit log & user management

API access is centralized in `src/lib/api.ts` (JWT bearer from localStorage).
