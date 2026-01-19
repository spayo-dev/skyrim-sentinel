# Skyrim Sentinel

**Supply Chain Security for the Skyrim Modding Ecosystem**

[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-F38020?logo=cloudflare)](https://workers.cloudflare.com/)
[![Python 3.14+](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)

<img width="894" height="628" alt="Screenshot 2026-01-18 212544" src="https://github.com/user-attachments/assets/8f8ed19d-cae9-4454-8fd6-8aa1ac8695a3" />

---

## Overview

Sentinel is a client-side integrity verification tool for SKSE (Skyrim Script Extender) plugins. It implements a **Zero Trust** model for the modding ecosystem by verifying DLL file hashes against a curated "Golden Set" database.

### The Problem

```mermaid
flowchart LR
    subgraph Threat Model
        A[Mod Author Account] -->|Compromised| B[Malicious DLL Upload]
        B --> C[Nexus Mods CDN]
        C --> D[User Downloads]
        D --> E[🔴 Malware Executed]
    end
```

- Users download compiled binaries (`.dll`) from Nexus without verification
- Compromised accounts can distribute malware via "updates"
- No easy way to verify if a DLL matches the official release

### The Solution

```mermaid
flowchart LR
    subgraph Sentinel Verification
        A[User's Mod Folder] -->|Scan| B[SHA-256 Hashes]
        B -->|Verify| C[Edge API]
        C -->|Lookup| D[(Golden Set DB)]
        D --> E{Match?}
        E -->|✅ Yes| F[Verified Safe]
        E -->|❌ No| G[Unknown/Alert]
    end
```

---

## Architecture

```mermaid
graph TB
    subgraph Client ["🖥️ Desktop Client (Python)"]
        UI[CustomTkinter UI]
        Scanner[DLL Scanner]
        Hasher[SHA-256 Hasher]
        Cache[(Local SQLite Cache)]
    end

    subgraph Edge ["☁️ Cloudflare Edge"]
        Worker[Hono Worker]
        KV[(KV Store)]
    end

    subgraph Tools ["🔧 Admin Tools"]
        Seeder[KV Seeder]
        GoldenSet[golden_set.json]
    end

    UI --> Scanner
    Scanner --> Hasher
    Hasher -->|POST /api/v1/scan| Worker
    Worker --> KV
    KV -->|Plugin Metadata| Worker
    Worker -->|JSON Response| UI
    
    Hasher -.->|Fallback| Cache
    
    GoldenSet --> Seeder
    Seeder -->|wrangler kv bulk| KV
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Desktop Client** | Python 3.14 + CustomTkinter | Scans mods folder, displays verification results |
| **Edge API** | Cloudflare Workers + Hono | Stateless hash verification endpoint |
| **Golden Set DB** | Cloudflare KV | Key-value store of verified plugin hashes |
| **Local Cache** | SQLite | Offline fallback when API unavailable |

---

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Client as Python Client
    participant Worker as CF Worker
    participant KV as Cloudflare KV

    User->>Client: Select MO2/mods folder
    Client->>Client: Scan for .dll files
    Client->>Client: Generate SHA-256 hashes
    
    Client->>Worker: POST /api/v1/scan {hashes: [...]}
    Worker->>KV: Batch lookup sha256:hash
    KV-->>Worker: Plugin metadata or null
    Worker-->>Client: {verified: N, unknown: M, results: [...]}
    
    Client->>User: Display color-coded results
    
    Note over Client: 🟢 Verified = Known safe hash
    Note over Client: 🟡 Unknown = Not in database
    Note over Client: 🔴 Revoked = Known malicious
```

---

## Project Structure

```
skyrim-sentinel/
├── sentinel-client/          # Python desktop application
│   ├── main.py              # Entry point
│   ├── scanner.py           # DLL discovery & hashing
│   ├── api_client.py        # API client + hybrid verifier
│   ├── local_cache.py       # SQLite offline cache
│   └── ui/
│       └── app.py           # CustomTkinter GUI
│
├── sentinel-worker/          # Cloudflare Worker (TypeScript)
│   ├── src/
│   │   ├── index.ts         # Hono routes
│   │   └── types.ts         # Type definitions
│   └── wrangler.jsonc       # Worker configuration
│
└── tools/                    # Admin utilities
    ├── golden_set.json      # Curated plugin database
    ├── seed_kv.ts           # KV bulk uploader
    ├── hasher.py            # CLI hash utility
    └── sync_golden_set.py   # Sync scan results to golden set
```

---

## Quick Start

### Client

```bash
cd sentinel-client
uv sync                    # Install dependencies
uv run python main.py      # Launch GUI
```

### Worker (Development)

```bash
cd sentinel-worker
npm install
npx wrangler dev           # Local dev server on :8787
```

### Deploy to Production

```bash
cd sentinel-worker
npx wrangler deploy        # Deploy to Cloudflare

cd ../tools
npx ts-node seed_kv.ts     # Seed KV with golden_set.json
```

---

## API Reference

### `POST /api/v1/scan`

Verify a batch of SHA-256 hashes against the Golden Set.

**Request:**
```json
{
  "hashes": [
    "44f679d547244fb60bd10f9e705ba1d0ee421e4951ebc211070fe5240b54f14a",
    "1aff9914d9685c16f7dce11882186ca5dd15402c37159bc45ce1584ab3475e70"
  ]
}
```

**Response:**
```json
{
  "scanned": 2,
  "verified": 1,
  "unknown": 1,
  "revoked": 0,
  "timestamp": "2026-01-18T12:00:00.000Z",
  "results": [
    {
      "hash": "44f679d547244fb60bd10f9e705ba1d0...",
      "status": "verified",
      "plugin": {
        "name": "Engine Fixes",
        "nexusId": 17230,
        "filename": "EngineFixes.dll",
        "author": "aers"
      }
    },
    {
      "hash": "1aff9914d9685c16f7dce11882186ca5...",
      "status": "unknown",
      "plugin": null
    }
  ]
}
```

### `GET /health`

Health check endpoint.

```json
{
  "status": "ok",
  "timestamp": "2026-01-18T12:00:00.000Z",
  "version": "1.0.0"
}
```

---

## Hybrid Verification Mode

```mermaid
flowchart TD
    A[Start Verification] --> B{Remote API Available?}
    B -->|Yes| C[Query Cloudflare Worker]
    C --> D[Return Remote Results]
    B -->|No / Timeout| E[Query Local SQLite Cache]
    E --> F[Return Cached Results]
    
    D --> G[Display to User]
    F --> G
    
    style C fill:#22c55e
    style E fill:#eab308
```

The client uses a **remote-first, local-fallback** strategy:

1. **Remote (Primary):** Queries the Cloudflare Worker for up-to-date security data
2. **Local (Fallback):** Uses SQLite cache populated from `golden_set.json` when offline

---

## Golden Set Database

The Golden Set contains verified hashes for trusted SKSE plugins:

| Plugin | Nexus ID | Files |
|--------|----------|-------|
| SSE Engine Fixes | 17230 | EngineFixes.dll |
| powerofthree's Tweaks | 51073 | po3_Tweaks.dll |
| Scrambled Bugs | 43532 | ScrambledBugs.dll |
| RaceMenu | 19080 | skee64.dll |
| ... | ... | ... |

**Current Coverage:** 100+ verified plugin DLLs

---

## Security Model

```mermaid
flowchart TB
    subgraph Trust Boundaries
        A[Untrusted: User's DLL Files]
        B[Trusted: Golden Set Hashes]
        C[Trusted: Cloudflare KV]
    end
    
    A -->|SHA-256| D{Hash Match?}
    B --> D
    C --> D
    
    D -->|Match| E[✅ Integrity Verified]
    D -->|No Match| F[⚠️ Unknown Origin]
```

**Key Principles:**

- **Zero Trust:** Every DLL is unverified until proven otherwise
- **Cryptographic Verification:** SHA-256 provides collision resistance
- **Edge-First:** Cloudflare's global network ensures low latency
- **Offline Capable:** Local cache enables air-gapped operation

---

## License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)



