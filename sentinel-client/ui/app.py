"""
Skyrim Sentinel - Main Application Window
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from api_client import SentinelAPIError, SentinelClient
from scanner import scan_directory
from version import __version__

# Theme configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ResultsTable(ctk.CTkScrollableFrame):
    """Scrollable table for displaying scan results."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=0)
        self.rows = []
        self.master_app = master  # Reference to copy to clipboard

        # Header
        self._add_header()

    def _add_header(self):
        """Add table header row."""
        ctk.CTkLabel(self, text="File", font=("", 13, "bold"), anchor="w").grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )

        ctk.CTkLabel(self, text="Status", font=("", 13, "bold")).grid(
            row=0, column=1, padx=10, pady=5
        )

        ctk.CTkLabel(self, text="Plugin", font=("", 13, "bold"), anchor="w").grid(
            row=0, column=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkLabel(self, text="Hash", font=("", 13, "bold"), anchor="w").grid(
            row=0, column=3, padx=10, pady=5, sticky="w"
        )

    def clear(self):
        """Clear all result rows."""
        for widgets in self.rows:
            for widget in widgets:
                widget.destroy()
        self.rows = []

    def _copy_hash(self, full_hash: str):
        """Copy hash to clipboard and show feedback."""
        self.master_app.clipboard_clear()
        self.master_app.clipboard_append(full_hash)
        # Brief visual feedback via status
        if hasattr(self.master_app, "_update_status"):
            self.master_app._update_status(f"Copied: {full_hash[:16]}...")

    def add_result(
        self, filename: str, status: str, plugin_name: str | None, sha256: str | None = None
    ):
        """Add a result row with color-coded status."""
        row = len(self.rows) + 1

        # Status colors
        colors = {
            "verified": "#22c55e",  # Green
            "unknown": "#eab308",  # Yellow
            "revoked": "#ef4444",  # Red
            "error": "#6b7280",  # Gray
        }
        color = colors.get(status, "#6b7280")

        # Filename
        file_label = ctk.CTkLabel(self, text=filename, anchor="w")
        file_label.grid(row=row, column=0, padx=10, pady=3, sticky="w")

        # Status badge
        status_label = ctk.CTkLabel(
            self,
            text=status.upper(),
            text_color=color,
            font=("", 12, "bold"),
        )
        status_label.grid(row=row, column=1, padx=10, pady=3)

        # Plugin name
        plugin_text = plugin_name or "—"
        plugin_label = ctk.CTkLabel(self, text=plugin_text, anchor="w")
        plugin_label.grid(row=row, column=2, padx=10, pady=3, sticky="w")

        # Hash (truncated, clickable to copy)
        if sha256:
            hash_btn = ctk.CTkButton(
                self,
                text=f"{sha256[:12]}...",
                font=("", 10),
                width=100,
                height=24,
                fg_color="transparent",
                text_color="#888888",
                hover_color="#333333",
                command=lambda h=sha256: self._copy_hash(h),
            )
            hash_btn.grid(row=row, column=3, padx=10, pady=3, sticky="w")
            self.rows.append((file_label, status_label, plugin_label, hash_btn))
        else:
            hash_label = ctk.CTkLabel(self, text="—", text_color="#555555")
            hash_label.grid(row=row, column=3, padx=10, pady=3, sticky="w")
            self.rows.append((file_label, status_label, plugin_label, hash_label))


class SentinelApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title(f"🛡️ Skyrim Sentinel v{__version__}")
        self.geometry("900x600")
        self.minsize(700, 400)

        # API client
        self.api = SentinelClient()

        # State
        self.selected_path: Path | None = None
        self.is_scanning = False
        self.last_scan_results: list[dict] = []  # Store for export

        self._create_widgets()

    def _create_widgets(self):
        """Create and layout all widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="🛡️ Skyrim Sentinel",
            font=("", 24, "bold"),
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10))

        subtitle = ctk.CTkLabel(
            self,
            text="SKSE Plugin Integrity Checker",
            text_color="#888888",
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Folder selection frame
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        self.path_label = ctk.CTkLabel(folder_frame, text="No folder selected", anchor="w")
        self.path_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

        browse_btn = ctk.CTkButton(
            folder_frame, text="Browse...", command=self._select_folder, width=100
        )
        browse_btn.grid(row=1, column=0, padx=10, pady=10)

        self.scan_btn = ctk.CTkButton(
            folder_frame,
            text="Scan",
            command=self._start_scan,
            state="disabled",
            fg_color="#22c55e",
            hover_color="#16a34a",
        )
        self.scan_btn.grid(row=1, column=1, padx=10, pady=10, sticky="e")

        # Progress bar
        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="ew")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="#888888")
        self.status_label.grid(row=4, column=0, padx=20, pady=5)

        # Results table
        self.results_table = ResultsTable(self)
        self.results_table.grid(row=5, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.grid_rowconfigure(5, weight=1)

        # Footer with version and export button
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="ew")
        footer_frame.grid_columnconfigure(1, weight=1)

        self.export_btn = ctk.CTkButton(
            footer_frame,
            text="Export Unknown",
            command=self._export_unknown,
            state="disabled",
            width=120,
            height=28,
            fg_color="#eab308",
            hover_color="#ca8a04",
            text_color="#000000",
            font=("", 11),
        )
        self.export_btn.grid(row=0, column=0, sticky="w")

        version_label = ctk.CTkLabel(
            footer_frame,
            text=f"v{__version__} • Beta",
            text_color="#555555",
            font=("", 11),
        )
        version_label.grid(row=0, column=1, sticky="e")

    def _select_folder(self):
        """Open folder picker dialog."""
        path = filedialog.askdirectory(
            title="Select MO2 Mods Folder",
            mustexist=True,
        )
        if path:
            self.selected_path = Path(path)
            display_path = str(self.selected_path)
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.path_label.configure(text=display_path)
            self.scan_btn.configure(state="normal")

    def _start_scan(self):
        """Start the scanning process in a background thread."""
        if self.is_scanning or not self.selected_path:
            return

        self.is_scanning = True
        self.scan_btn.configure(state="disabled")
        self.results_table.clear()
        self.progress.set(0)

        # Run in background thread
        thread = threading.Thread(target=self._scan_thread, daemon=True)
        thread.start()

    def _scan_thread(self):
        """Background scanning thread."""
        try:
            # Phase 1: Find and hash DLLs
            self._update_status("Scanning for DLLs...")

            def progress_callback(current, total, filename):
                progress = current / total if total > 0 else 0
                self.after(0, lambda: self.progress.set(progress * 0.5))
                self.after(0, lambda: self._update_status(f"Hashing: {filename}"))

            scan_results = scan_directory(self.selected_path, progress_callback)

            if not scan_results:
                self._update_status("No DLL files found")
                self._finish_scan()
                return

            # Filter out errors and get hashes
            valid_results = [r for r in scan_results if r.get("sha256")]
            hashes = [r["sha256"] for r in valid_results]

            if not hashes:
                self._update_status("No valid DLL files to verify")
                self._finish_scan()
                return

            # Phase 2: Verify with API
            self._update_status("Verifying hashes...")
            self.after(0, lambda: self.progress.set(0.6))

            try:
                api_response = self.api.scan(hashes)
                self.after(0, lambda: self.progress.set(0.9))

                # Build hash -> result mapping
                hash_to_result = {r.hash: r for r in api_response.results}

                # Store results for export and display
                combined_results = []
                for local_result in valid_results:
                    h = local_result["sha256"]
                    api_result = hash_to_result.get(h)

                    status = api_result.status if api_result else "unknown"
                    plugin = api_result.plugin.name if api_result and api_result.plugin else None

                    combined_results.append(
                        {
                            "filename": local_result["filename"],
                            "path": local_result.get("path", ""),
                            "sha256": h,
                            "size_bytes": local_result.get("size_bytes", 0),
                            "status": status,
                            "plugin": plugin,
                        }
                    )

                    self.after(
                        0,
                        lambda f=local_result["filename"],
                        s=status,
                        p=plugin,
                        h=h: self.results_table.add_result(f, s, p, h),
                    )

                # Store for export
                self.last_scan_results = combined_results

                # Enable export if there are unknowns
                unknown_count = sum(1 for r in combined_results if r["status"] == "unknown")
                if unknown_count > 0:
                    self.after(0, lambda: self.export_btn.configure(state="normal"))

                # Add errors
                for r in scan_results:
                    if r.get("error"):
                        err_filename = r["filename"]
                        err_msg = r.get("error")
                        self.after(
                            0,
                            lambda f=err_filename, e=err_msg: self.results_table.add_result(
                                f, "error", e
                            ),
                        )

                # Summary
                summary = f"Done: {api_response.verified} verified, {api_response.unknown} unknown"
                if api_response.revoked > 0:
                    summary += f", {api_response.revoked} REVOKED!"
                self._update_status(summary)

            except SentinelAPIError as e:
                self._update_status(f"API Error: {e}")
            except Exception as e:
                self._update_status(f"Connection Error: {e}")
                # Still show local results as unknown
                for r in valid_results:
                    h = r["sha256"]
                    self.after(
                        0,
                        lambda f=r["filename"], h=h: self.results_table.add_result(
                            f, "unknown", "API unavailable", h
                        ),
                    )
                # Store for offline export
                self.last_scan_results = [
                    {
                        "filename": r["filename"],
                        "path": r.get("path", ""),
                        "sha256": r["sha256"],
                        "size_bytes": r.get("size_bytes", 0),
                        "status": "unknown",
                        "plugin": None,
                    }
                    for r in valid_results
                ]
                self.after(0, lambda: self.export_btn.configure(state="normal"))

        except Exception as e:
            self._update_status(f"Error: {e}")
        finally:
            self._finish_scan()

    def _update_status(self, text: str):
        """Update status label (thread-safe)."""
        self.after(0, lambda: self.status_label.configure(text=text))

    def _finish_scan(self):
        """Reset scan state."""
        self.after(0, lambda: self.progress.set(1.0))
        self.after(0, lambda: self.scan_btn.configure(state="normal"))
        self.is_scanning = False

    def _export_unknown(self):
        """Export unknown hashes to JSON for submission."""
        unknown = [r for r in self.last_scan_results if r["status"] == "unknown"]

        if not unknown:
            self._update_status("No unknown hashes to export")
            return

        # Ask user where to save
        filepath = filedialog.asksaveasfilename(
            title="Export Unknown Hashes",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"sentinel_unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        if not filepath:
            return

        # Format for submission
        export_data = {
            "sentinel_version": __version__,
            "exported_at": datetime.now().isoformat(),
            "instructions": "Submit this file to the Skyrim Sentinel project to help expand the database.",
            "unknown_plugins": [
                {
                    "filename": r["filename"],
                    "sha256": r["sha256"],
                    "size_bytes": r["size_bytes"],
                    "source_path": r["path"],
                    "mod_name": "",  # User can fill this in
                    "nexus_id": None,  # User can fill this in
                }
                for r in unknown
            ],
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            self._update_status(f"Exported {len(unknown)} unknown hashes")
        except OSError as e:
            self._update_status(f"Export failed: {e}")


def main():
    """Application entry point."""
    app = SentinelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
