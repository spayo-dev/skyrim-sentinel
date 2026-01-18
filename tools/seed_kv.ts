/**
 * Skyrim Sentinel - KV Seeder
 *
 * Seeds Cloudflare KV with data from golden_set.json.
 * Uses wrangler bulk upload for efficient writes.
 *
 * Usage:
 *   npx ts-node seed_kv.ts [--preview] [--namespace <id>]
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

interface FileEntry {
	filename: string;
	sha256: string | null;
	status?: string;
}

interface Plugin {
	name: string;
	nexusId: number;
	author?: string;
	files: FileEntry[];
}

interface GoldenSet {
	version: string;
	plugins: Plugin[];
}

interface KVEntry {
	key: string;
	value: string;
}

function loadGoldenSet(): GoldenSet {
	const path = join(__dirname, "golden_set.json");
	const content = readFileSync(path, "utf-8");
	return JSON.parse(content) as GoldenSet;
}

function convertToKVEntries(goldenSet: GoldenSet): KVEntry[] {
	const entriesMap = new Map<string, KVEntry>();

	for (const plugin of goldenSet.plugins) {
		for (const file of plugin.files) {
			if (!file.sha256) continue;

			const key = `sha256:${file.sha256}`;

			// Check for duplicate keys
			if (entriesMap.has(key)) {
				const existingEntry = entriesMap.get(key);
				const existing = existingEntry ? JSON.parse(existingEntry.value) : null;
				console.warn(
					`[!] Duplicate hash found: ${file.sha256.slice(0, 16)}...`,
				);
				console.warn(`    Existing: ${existing?.name} (${existing?.filename})`);
				console.warn(
					`    New: ${plugin.name} (${file.filename}) - keeping this one`,
				);
			}

			entriesMap.set(key, {
				key,
				value: JSON.stringify({
					name: plugin.name,
					nexusId: plugin.nexusId,
					filename: file.filename,
					status: file.status ?? "verified",
					author: plugin.author,
				}),
			});
		}
	}

	return Array.from(entriesMap.values());
}

function seedKV(preview: boolean, namespaceId?: string): void {
	const goldenSet = loadGoldenSet();
	const entries = convertToKVEntries(goldenSet);

	if (entries.length === 0) {
		console.log(
			"[!] No hashes found in golden_set.json. Add file hashes first.",
		);
		console.log(
			"    Use: python hasher.py scan <directory> to generate hashes.",
		);
		return;
	}

	// Write to temp file for bulk upload
	const bulkPath = join(__dirname, "kv_bulk.json");
	writeFileSync(bulkPath, JSON.stringify(entries, null, 2));
	console.log(`[+] Prepared ${entries.length} entries for upload.`);

	// Build wrangler command
	const bindingFlag = namespaceId
		? `--namespace-id=${namespaceId}`
		: "--binding=SENTINEL_HASHES";

	const previewFlag = preview ? "--preview" : "";

	// Ensure forward slashes for Windows compatibility in shell command
	const safeBulkPath = bulkPath.replace(/\\/g, "/");

	const cmd =
		`npx wrangler kv bulk put "${safeBulkPath}" ${bindingFlag} ${previewFlag}`.trim();

	console.log(`[+] Running: ${cmd}`);

	try {
		execSync(cmd, {
			cwd: join(__dirname, "..", "sentinel-worker"),
			stdio: "inherit",
		});
		console.log("[+] KV seeding complete.");
	} catch {
		console.error("[!] Wrangler command failed. Is wrangler configured?");
		process.exit(1);
	}
}

// CLI
const args = process.argv.slice(2);
const preview = args.includes("--preview");
const nsIndex = args.indexOf("--namespace");
const namespaceId = nsIndex !== -1 ? args[nsIndex + 1] : undefined;

seedKV(preview, namespaceId);
