# Built — maintenance log (canonical)

Asset and maintenance tracking for construction work: materials, projects,
tasks, and activity — a **maintenance log**, not a full ERP.

This repo is the **canonical** home for that product story. The overlapping
`forgesure` experiment is superseded; see
[kuyacarlo/forgesure](https://github.com/kuyacarlo/forgesure) for the pointer
README only (that repo is not deleted).

Stack: Python API (`api/`) + Next.js frontend (`frontend/`).

## Related

| Repo | Role |
|------|------|
| **this repo (`built`)** | Canonical maintenance-log README and app |
| [`forgesure`](https://github.com/kuyacarlo/forgesure) | Superseded product story → points here |

## Installation

### Fullstack

```sh
docker compose up -d
```

### Manual

#### Backend

```sh
cd api
python main.py
```

#### Frontend (dev)

```sh
cd frontend
pnpm run dev
```

#### Frontend (prod)

```sh
cd frontend
pnpm run build
pnpm run start
```
