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
	const entries: KVEntry[] = [];

	for (const plugin of goldenSet.plugins) {
		for (const file of plugin.files) {
			if (!file.sha256) continue;

			entries.push({
				key: `sha256:${file.sha256}`,
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

	return entries;
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

	const cmd = `npx wrangler kv key bulk put ${bindingFlag} ${previewFlag} "${bulkPath}"`;

	console.log(`[+] Running: ${cmd}`);

	try {
		execSync(cmd, {
			cwd: join(__dirname, "..", "sentinel-worker"),
			stdio: "inherit",
		});
		console.log("[+] KV seeding complete.");
	} catch (error: unknown) {
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
