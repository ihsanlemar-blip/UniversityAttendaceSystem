# API Contracts & Type Definitions

This directory serves as the **single source of truth** for API schemas and cross-system client contracts.

---

## Directory Purpose

1. **`openapi.json`**: Generated OpenAPI 3.1 schema exported directly from FastAPI (`/api/v1/openapi.json`).
2. **`typescript/`**: Generated TypeScript types and API client consumed by `apps/web/`.
3. **`dart/`**: Generated Dart data transfer models consumed by `apps/mobile/`.

---

## Generation Pipeline (Milestone 4+)

When API models or routes in `backend/app/` are added or updated:
```bash
# 1. Export OpenAPI snapshot
python scripts/export_openapi.py contracts/openapi.json

# 2. Generate TypeScript types for Next.js web client
npm --prefix apps/web run generate:api

# 3. Generate Dart models for Flutter mobile client
cd apps/mobile && dart run build_runner build
```

This automated pipeline prevents manual schema drift between the FastAPI backend and frontend clients.
