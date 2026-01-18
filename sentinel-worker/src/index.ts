import { Hono } from "hono";
import { cors } from "hono/cors";
import type { ErrorResponse, KVPluginEntry, ScanRequest, ScanResponse, ScanResult } from "./types";

// ============================================================================
// App Configuration
// ============================================================================

type Bindings = {
	SENTINEL_HASHES: KVNamespace;
};

const app = new Hono<{ Bindings: Bindings }>();

// ============================================================================
// Middleware
// ============================================================================

app.use("/*", cors());

// Global error handler
app.onError((err, c) => {
	console.error("Unhandled error:", err);
	const response: ErrorResponse = {
		error: "Internal server error",
		code: "INTERNAL_ERROR",
	};
	return c.json(response, 500);
});

// ============================================================================
// Routes
// ============================================================================

// Root endpoint
app.get("/", (c) => c.text("Skyrim Sentinel API is running."));

// Health check
app.get("/health", (c) =>
	c.json({
		status: "ok",
		timestamp: new Date().toISOString(),
		version: "1.0.0",
	}),
);

// Scan endpoint - verify hashes against Golden Set
app.post("/api/v1/scan", async (c) => {
	// Parse request body
	let body: ScanRequest;
	try {
		body = await c.req.json<ScanRequest>();
	} catch {
		const response: ErrorResponse = {
			error: "Invalid JSON",
			code: "INVALID_JSON",
		};
		return c.json(response, 400);
	}

	// Validate request
	if (!body.hashes || !Array.isArray(body.hashes)) {
		const response: ErrorResponse = {
			error: "Missing or invalid 'hashes' field",
			code: "INVALID_REQUEST",
			details: "Expected { hashes: string[] }",
		};
		return c.json(response, 400);
	}

	if (body.hashes.length === 0) {
		const response: ErrorResponse = {
			error: "Empty hashes array",
			code: "EMPTY_HASHES",
		};
		return c.json(response, 400);
	}

	// Limit batch size to prevent abuse
	const MAX_BATCH_SIZE = 500;
	if (body.hashes.length > MAX_BATCH_SIZE) {
		const response: ErrorResponse = {
			error: `Batch size exceeds limit of ${MAX_BATCH_SIZE}`,
			code: "BATCH_TOO_LARGE",
		};
		return c.json(response, 400);
	}

	// Validate hash format (should be 64 hex chars for SHA-256)
	const hashRegex = /^[a-f0-9]{64}$/i;
	const invalidHashes = body.hashes.filter((h) => !hashRegex.test(h));
	if (invalidHashes.length > 0) {
		const response: ErrorResponse = {
			error: "Invalid hash format",
			code: "INVALID_HASH_FORMAT",
			details: `Expected SHA-256 (64 hex chars). Invalid: ${invalidHashes.slice(0, 3).join(", ")}${invalidHashes.length > 3 ? "..." : ""}`,
		};
		return c.json(response, 400);
	}

	// Normalize hashes to lowercase
	const normalizedHashes = body.hashes.map((h) => h.toLowerCase());

	// Lookup each hash in KV
	const results: ScanResult[] = [];
	let verified = 0;
	let unknown = 0;
	let revoked = 0;

	// Process in parallel for better performance
	const lookupPromises = normalizedHashes.map(async (hash) => {
		const key = `sha256:${hash}`;
		const value = await c.env.SENTINEL_HASHES.get(key);

		if (value === null) {
			unknown++;
			return {
				hash,
				status: "unknown" as const,
				plugin: null,
			};
		}

		// Parse stored plugin info
		try {
			const pluginData: KVPluginEntry = JSON.parse(value);

			if (pluginData.status === "revoked") {
				revoked++;
			} else {
				verified++;
			}

			return {
				hash,
				status: pluginData.status === "revoked" ? "revoked" : "verified",
				plugin: {
					name: pluginData.name,
					nexusId: pluginData.nexusId,
					filename: pluginData.filename,
					author: pluginData.author,
				},
			} as ScanResult;
		} catch {
			// Malformed KV entry - treat as unknown
			unknown++;
			return {
				hash,
				status: "unknown" as const,
				plugin: null,
			};
		}
	});

	const lookupResults = await Promise.all(lookupPromises);
	results.push(...lookupResults);

	// Build response
	const response: ScanResponse = {
		scanned: results.length,
		verified,
		unknown,
		revoked,
		timestamp: new Date().toISOString(),
		results,
	};

	return c.json(response);
});

export default app;
