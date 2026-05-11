"""Tkinter GUI for pypi-profile CLI commands."""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, scrolledtext, ttk

COMMANDS: list[dict] = [
    {
        "name": "doctor",
        "label": "Doctor",
        "help": (
            "Diagnose local configuration and profile health.\n\n"
            "Checks that all required and optional Python dependencies are installed "
            "and that a minisign secret key exists.\n\n"
            "No arguments required — runs automatically."
        ),
        "args": [],
        "readonly": True,
    },
    {
        "name": "inspect",
        "label": "Inspect",
        "help": (
            "Inspect a profile package or TOML file without executing any plugin code.\n\n"
            "Prints a quick summary: principal name, PyPI username, number of packages, "
            "projects, humans, and whether a signing key is configured.\n\n"
            "Source: path to a pypi_profile.toml file, a directory containing one, "
            "or an installed profile package name."
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
        ],
        "readonly": True,
    },
    {
        "name": "validate",
        "label": "Validate",
        "help": (
            "Validate a pypi_profile.toml file against the Pydantic schema.\n\n"
            "Reports OK with a brief summary on success, or prints detailed "
            "validation errors on failure.\n\n"
            "Path: the .toml file to validate (default: pypi_profile.toml in the current directory)."
        ),
        "args": [
            {
                "flag": "path",
                "label": "Path to .toml",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
        ],
        "readonly": True,
    },
    {
        "name": "dump",
        "label": "Dump JSON",
        "help": (
            "Dump the parsed profile as pretty-printed JSON.\n\n"
            "Useful for debugging the data model or piping into other tools.\n\n"
            "Source: path to a pypi_profile.toml, a directory, or a package name."
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
        ],
        "readonly": True,
    },
    {
        "name": "fetch",
        "label": "Fetch",
        "help": (
            "Fetch live metadata from PyPI, GitHub, GitLab, and Mastodon.\n\n"
            "Compares the packages declared in the profile against what is actually "
            "published on PyPI and prints a reconciliation report.\n\n"
            "Source: path to a pypi_profile.toml, a directory, or a package name.\n"
            "--json: also print the raw API responses as JSON."
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
            {
                "flag": "--json",
                "label": "Print raw JSON",
                "default": False,
                "kind": "bool",
            },
        ],
        "readonly": True,
    },
    {
        "name": "verify",
        "label": "Verify Claims",
        "help": (
            "Verify proof-of-control claims for all [[profiles]] entries.\n\n"
            "Fetches each declared URL and looks for the signed proof string embedded "
            "in the page.  Requires a public_key in the [verification] section.\n\n"
            "Source: path to a pypi_profile.toml, a directory, or a package name.\n"
            "--profile-package: override the profile package name used in the claim message."
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
            {
                "flag": "--profile-package",
                "label": "Profile package name override",
                "default": "",
                "kind": "str",
            },
        ],
        "readonly": True,
    },
    {
        "name": "serve",
        "label": "Serve",
        "help": (
            "Start the FastAPI profile web server.\n\n"
            "Opens a local HTTP server so you can preview your profile in a browser.  "
            "Press Ctrl-C (or Stop) to shut it down.\n\n"
            "Source: path to a pypi_profile.toml, a directory, or a package name.\n"
            "--host: bind address (default: 127.0.0.1)\n"
            "--port: port number (default: 8000)\n"
            "--allow-code: enable plugin code execution (off by default for safety)"
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
            {"flag": "--host", "label": "Host", "default": "127.0.0.1", "kind": "str"},
            {"flag": "--port", "label": "Port", "default": "8000", "kind": "str"},
            {
                "flag": "--allow-code",
                "label": "Allow plugin code",
                "default": False,
                "kind": "bool",
            },
        ],
        "readonly": False,
    },
    {
        "name": "init",
        "label": "Init",
        "help": (
            "Create a starter pypi_profile.toml.\n\n"
            "Generates a skeleton profile file.  Use --fetch to pre-fill data from "
            "PyPI and GitHub.  Use --from-json-resume to import from a JSON Resume file.\n\n"
            "--username: your PyPI username\n"
            "--kind: individual / team / company / llc / foundation / collective / project / other\n"
            "--output: output path (default: pypi_profile.toml)\n"
            "--force: overwrite an existing file\n"
            "--fetch: fetch live data from PyPI / GitHub\n"
            "--from-json-resume: path to a resume.json file"
        ),
        "args": [
            {
                "flag": "--username",
                "label": "PyPI username",
                "default": "",
                "kind": "str",
            },
            {
                "flag": "--kind",
                "label": "Kind",
                "default": "individual",
                "kind": "choice",
                "choices": [
                    "individual",
                    "team",
                    "company",
                    "llc",
                    "foundation",
                    "collective",
                    "project",
                    "other",
                ],
            },
            {
                "flag": "--output",
                "label": "Output path",
                "default": "pypi_profile.toml",
                "kind": "str",
            },
            {
                "flag": "--force",
                "label": "Force overwrite",
                "default": False,
                "kind": "bool",
            },
            {
                "flag": "--fetch",
                "label": "Fetch live data",
                "default": False,
                "kind": "bool",
            },
            {
                "flag": "--from-json-resume",
                "label": "JSON Resume path",
                "default": "",
                "kind": "file",
            },
        ],
        "extra_argv": ["--no-interactive"],
        "readonly": False,
    },
    {
        "name": "keygen",
        "label": "Keygen",
        "help": (
            "Generate a minisign keypair for signing profile claims.\n\n"
            "Creates a secret key and a public key.  The public key's base-64 value "
            "should be placed in the [verification] public_key field of your profile.\n\n"
            "--key-dir: directory to write the key files (default: ~/.pypi_profile/)\n"
            "--password: optional password to encrypt the secret key\n"
            "--force: overwrite existing key files"
        ),
        "args": [
            {
                "flag": "--key-dir",
                "label": "Key directory",
                "default": "~/.pypi_profile/",
                "kind": "dir",
            },
            {
                "flag": "--password",
                "label": "Password (optional)",
                "default": "",
                "kind": "password",
            },
            {
                "flag": "--force",
                "label": "Force overwrite",
                "default": False,
                "kind": "bool",
            },
        ],
        "readonly": False,
    },
    {
        "name": "sign",
        "label": "Sign Claim",
        "help": (
            "Sign a controls-url claim and print the proof string.\n\n"
            "Use this to prove you control an external URL (GitHub profile, website, etc.).  "
            "Copy the printed proof string and place it at the target URL.\n\n"
            "Source: path to a pypi_profile.toml, a directory, or a package name.\n"
            "--url: the URL you are asserting control over (required)\n"
            "--key: path to your secret key file\n"
            "--password: password for the secret key\n"
            "--profile-package: override the profile package name"
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
            {
                "flag": "--url",
                "label": "URL to sign (required)",
                "default": "",
                "kind": "str",
            },
            {
                "flag": "--key",
                "label": "Secret key path",
                "default": "~/.pypi_profile/minisign.key",
                "kind": "file",
            },
            {
                "flag": "--password",
                "label": "Key password",
                "default": "",
                "kind": "password",
            },
            {
                "flag": "--profile-package",
                "label": "Profile package name override",
                "default": "",
                "kind": "str",
            },
        ],
        "readonly": False,
    },
]

HELP_INTRO = (
    "pypi-profile GUI\n"
    "================\n\n"
    "Select a command from the left panel.\n\n"
    "Read-only commands (Doctor, Inspect, Validate, Dump, Fetch, Verify) "
    "run automatically when selected.\n\n"
    "Write commands (Serve, Init, Keygen, Sign) require you to fill in "
    "the arguments and press Run.\n\n"
    "Use the Browse buttons to pick files or directories interactively."
)


class PypiProfileGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("pypi-profile GUI")
        self.geometry("1100x680")
        self.minsize(900, 500)
        self._running_proc: subprocess.Popen | None = None
        self._current_cmd: dict | None = None
        self._arg_widgets: dict[str, tk.Variable] = {}

        default_key = str(Path("~/.pypi_profile/minisign.key").expanduser())
        self._global_key_path = tk.StringVar(value=default_key)
        self._global_key_password = tk.StringVar(value="")

        self._build_ui()
        self._select_command(COMMANDS[0])

    def _build_ui(self) -> None:
        mono = font.Font(family="Courier New", size=10)

        # ── root grid: 3 columns ──────────────────────────────────────────
        self.columnconfigure(0, weight=0, minsize=160)
        self.columnconfigure(1, weight=3)
        self.columnconfigure(2, weight=1, minsize=240)
        self.rowconfigure(0, weight=1)

        # ── LEFT panel ───────────────────────────────────────────────────
        left = tk.Frame(self, bd=1, relief=tk.SUNKEN, bg="#2b2b2b")
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        left.rowconfigure(0, weight=0)
        left.rowconfigure(1, weight=1)

        tk.Label(
            left,
            text="Commands",
            bg="#2b2b2b",
            fg="white",
            font=("Helvetica", 11, "bold"),
            pady=6,
        ).grid(row=0, column=0, sticky="ew")

        self._cmd_buttons: dict[str, tk.Button] = {}
        for i, cmd in enumerate(COMMANDS):
            btn = tk.Button(
                left,
                text=cmd["label"],
                anchor="w",
                padx=8,
                relief=tk.FLAT,
                bg="#2b2b2b",
                fg="#cccccc",
                activebackground="#444444",
                activeforeground="white",
                command=lambda c=cmd: self._select_command(c),
            )
            btn.grid(row=i + 1, column=0, sticky="ew", padx=2, pady=1)
            left.columnconfigure(0, weight=1)
            self._cmd_buttons[cmd["name"]] = btn

        # ── Key settings (bottom of left panel) ──────────────────────────
        sep_row = len(COMMANDS) + 1
        tk.Frame(left, bg="#555555", height=1).grid(
            row=sep_row, column=0, sticky="ew", padx=6, pady=(8, 4)
        )

        key_frame = tk.Frame(left, bg="#2b2b2b")
        key_frame.grid(row=sep_row + 1, column=0, sticky="ew", padx=6, pady=(0, 6))
        key_frame.columnconfigure(0, weight=1)

        tk.Label(
            key_frame,
            text="Key",
            bg="#2b2b2b",
            fg="#aaaaaa",
            font=("Helvetica", 9, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(
            key_frame,
            text="Path:",
            bg="#2b2b2b",
            fg="#aaaaaa",
            font=("Helvetica", 8),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        key_path_entry = tk.Entry(
            key_frame,
            textvariable=self._global_key_path,
            width=16,
            font=("Courier New", 8),
            bg="#1a1a1a",
            fg="#cccccc",
            insertbackground="white",
            relief=tk.FLAT,
        )
        key_path_entry.grid(row=2, column=0, sticky="ew", pady=(0, 2))
        tk.Button(
            key_frame,
            text="…",
            font=("Helvetica", 8),
            padx=2,
            pady=0,
            command=lambda: self._global_key_path.set(
                filedialog.askopenfilename(
                    title="Select secret key",
                    filetypes=[("Key files", "*.key"), ("All files", "*.*")],
                )
                or self._global_key_path.get()
            ),
        ).grid(row=2, column=1, padx=(2, 0))

        tk.Label(
            key_frame,
            text="Password:",
            bg="#2b2b2b",
            fg="#aaaaaa",
            font=("Helvetica", 8),
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))
        tk.Entry(
            key_frame,
            textvariable=self._global_key_password,
            show="*",
            width=16,
            font=("Courier New", 8),
            bg="#1a1a1a",
            fg="#cccccc",
            insertbackground="white",
            relief=tk.FLAT,
        ).grid(row=4, column=0, columnspan=2, sticky="ew")

        # ── CENTER panel ─────────────────────────────────────────────────
        center = tk.Frame(self)
        center.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        center.rowconfigure(0, weight=0)
        center.rowconfigure(1, weight=0)
        center.rowconfigure(2, weight=1)
        center.columnconfigure(0, weight=1)

        # Title
        self._title_var = tk.StringVar(value="")
        tk.Label(
            center,
            textvariable=self._title_var,
            font=("Helvetica", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        # Args frame (scrollable via canvas for tall forms)
        args_outer = tk.Frame(center, bd=1, relief=tk.GROOVE)
        args_outer.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        args_outer.columnconfigure(0, weight=1)
        self._args_frame = args_outer

        # Output
        out_label = tk.Label(
            center, text="Output", anchor="w", font=("Helvetica", 10, "bold")
        )
        out_label.grid(row=2, column=0, sticky="w")

        self._output = scrolledtext.ScrolledText(
            center, font=mono, bg="#1e1e1e", fg="#d4d4d4", wrap=tk.WORD
        )
        self._output.grid(row=3, column=0, sticky="nsew")
        center.rowconfigure(3, weight=1)

        # Run / Stop bar
        btn_bar = tk.Frame(center)
        btn_bar.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self._run_btn = tk.Button(
            btn_bar,
            text="Run",
            width=10,
            command=self._run_command,
            bg="#0e7c0e",
            fg="white",
        )
        self._run_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._stop_btn = tk.Button(
            btn_bar,
            text="Stop",
            width=10,
            command=self._stop_command,
            bg="#7c0e0e",
            fg="white",
            state=tk.DISABLED,
        )
        self._stop_btn.pack(side=tk.LEFT)
        self._status_var = tk.StringVar(value="")
        tk.Label(btn_bar, textvariable=self._status_var, fg="#888888").pack(
            side=tk.LEFT, padx=8
        )

        # ── RIGHT panel ──────────────────────────────────────────────────
        right = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        right.grid(row=0, column=2, sticky="nsew", padx=(0, 4), pady=4)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        tk.Label(
            right, text="Help", font=("Helvetica", 11, "bold"), anchor="w", pady=4
        ).grid(row=0, column=0, sticky="ew", padx=6)
        self._help_text = scrolledtext.ScrolledText(
            right,
            font=("Helvetica", 10),
            wrap=tk.WORD,
            bg="#f5f5f5",
            fg="#222222",
            relief=tk.FLAT,
        )
        self._help_text.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self._help_text.insert(tk.END, HELP_INTRO)
        self._help_text.config(state=tk.DISABLED)

    def _select_command(self, cmd: dict) -> None:
        self._stop_command()
        self._current_cmd = cmd

        # Highlight active button
        for name, btn in self._cmd_buttons.items():
            is_active = name == cmd["name"]
            btn.config(
                bg="#005f99" if is_active else "#2b2b2b",
                fg="white" if is_active else "#cccccc",
            )

        self._title_var.set(cmd["label"])
        self._build_args_form(cmd)
        self._update_help(cmd["help"])
        self._output.delete("1.0", tk.END)

        if cmd["readonly"]:
            self._run_btn.config(state=tk.DISABLED)
            self._run_command()
        else:
            self._run_btn.config(state=tk.NORMAL)

    def _build_args_form(self, cmd: dict) -> None:
        for w in self._args_frame.winfo_children():
            w.destroy()
        self._arg_widgets.clear()

        if not cmd["args"]:
            tk.Label(
                self._args_frame, text="No arguments needed.", fg="#888888", pady=4
            ).grid(row=0, column=0, columnspan=3, padx=8)
            return

        self._args_frame.columnconfigure(1, weight=1)
        for row_i, arg in enumerate(cmd["args"]):
            label = arg["label"]
            flag = arg["flag"]
            kind = arg["kind"]
            default = arg["default"]

            tk.Label(self._args_frame, text=label + ":", anchor="e").grid(
                row=row_i, column=0, sticky="e", padx=(8, 4), pady=3
            )

            if kind == "bool":
                var: tk.Variable = tk.BooleanVar(value=bool(default))
                tk.Checkbutton(self._args_frame, variable=var).grid(
                    row=row_i, column=1, sticky="w", pady=3
                )
                self._arg_widgets[flag] = var

            elif kind == "choice":
                var = tk.StringVar(value=str(default))
                cb = ttk.Combobox(
                    self._args_frame,
                    textvariable=var,
                    values=arg["choices"],
                    state="readonly",
                    width=24,
                )
                cb.grid(row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8))
                self._arg_widgets[flag] = var

            elif kind == "password":
                var = tk.StringVar(value=str(default))
                tk.Entry(self._args_frame, textvariable=var, show="*", width=36).grid(
                    row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8)
                )
                self._arg_widgets[flag] = var

            elif kind in ("file", "dir"):
                var = tk.StringVar(value=str(default))
                entry = tk.Entry(self._args_frame, textvariable=var, width=36)
                entry.grid(row=row_i, column=1, sticky="ew", pady=3)

                if kind == "file":
                    browse_cmd = lambda v=var: v.set(
                        filedialog.askopenfilename() or v.get()
                    )
                else:
                    browse_cmd = lambda v=var: v.set(
                        filedialog.askdirectory() or v.get()
                    )
                tk.Button(self._args_frame, text="Browse", command=browse_cmd).grid(
                    row=row_i, column=2, padx=(4, 8), pady=3
                )
                self._arg_widgets[flag] = var

            else:
                var = tk.StringVar(value=str(default))
                tk.Entry(self._args_frame, textvariable=var, width=36).grid(
                    row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8)
                )
                self._arg_widgets[flag] = var

    def _update_help(self, text: str) -> None:
        self._help_text.config(state=tk.NORMAL)
        self._help_text.delete("1.0", tk.END)
        self._help_text.insert(tk.END, text)
        self._help_text.config(state=tk.DISABLED)

    def _build_argv_and_env(self, cmd: dict) -> tuple[list[str], dict[str, str]]:
        """Return (argv, extra_env).  Passwords and key path are passed via env vars, not argv."""
        import os

        argv = [sys.executable, "-m", "pypi_profile.cli", cmd["name"]]
        extra_env: dict[str, str] = {}

        if cmd["name"] == "sign":
            argv.append("controls-url")

        argv.extend(cmd.get("extra_argv", []))

        for arg in cmd["args"]:
            flag = arg["flag"]
            kind = arg["kind"]
            var = self._arg_widgets.get(flag)
            if var is None:
                continue
            value = var.get()

            if kind == "bool":
                if value:
                    argv.append(flag)
            elif kind == "password":
                # Per-command password field overrides the global one for this run.
                if str(value).strip():
                    extra_env["PYPI_PROFILE_KEY_PASSWORD"] = str(value)
            elif flag.startswith("--"):
                if str(value).strip():
                    argv += [flag, str(value)]
            else:
                if str(value).strip():
                    argv.append(str(value))

        # Global key settings — applied to every command, not just sign/keygen.
        # Per-command password (above) wins if both are set.
        key_path = self._global_key_path.get().strip()
        key_password = self._global_key_password.get().strip()
        if key_path:
            extra_env.setdefault("PYPI_PROFILE_KEY_PATH", key_path)
        if key_password:
            extra_env.setdefault("PYPI_PROFILE_KEY_PASSWORD", key_password)

        env = {**os.environ, **extra_env}
        return argv, env

    def _run_command(self) -> None:
        cmd = self._current_cmd
        if cmd is None:
            return

        self._output.delete("1.0", tk.END)
        argv, env = self._build_argv_and_env(cmd)
        # Show the command without revealing env-var secrets
        self._append_output(f"$ {' '.join(argv)}\n\n")
        self._status_var.set("Running…")
        self._run_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)

        def worker() -> None:
            try:
                proc = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(Path.cwd()),
                    env=env,
                )
                self._running_proc = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    self._append_output(line)
                proc.wait()
                self._running_proc = None
                rc = proc.returncode
                self.after(0, lambda: self._on_done(rc, cmd))
            except Exception as exc:
                self._append_output(f"\nERROR: {exc}\n")
                self._running_proc = None
                self.after(0, lambda: self._on_done(1, cmd))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, rc: int, cmd: dict) -> None:
        self._stop_btn.config(state=tk.DISABLED)
        if not cmd["readonly"]:
            self._run_btn.config(state=tk.NORMAL)
        color = "#0e7c0e" if rc == 0 else "#7c0e0e"
        msg = f"Exited {rc}"
        self._status_var.set(msg)
        self._append_output(f"\n[{msg}]\n")
        self.after(5000, lambda: self._status_var.set(""))

    def _stop_command(self) -> None:
        if self._running_proc is not None:
            try:
                self._running_proc.terminate()
            except OSError:
                pass
            self._running_proc = None
        self._stop_btn.config(state=tk.DISABLED)
        if self._current_cmd and not self._current_cmd["readonly"]:
            self._run_btn.config(state=tk.NORMAL)
        self._status_var.set("")

    def _append_output(self, text: str) -> None:
        def _do() -> None:
            self._output.insert(tk.END, text)
            self._output.see(tk.END)

        self.after(0, _do)


def main() -> None:
    app = PypiProfileGui()
    app.mainloop()


if __name__ == "__main__":
    main()
