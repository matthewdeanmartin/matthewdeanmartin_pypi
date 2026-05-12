"""Tkinter GUI for pypi-profile CLI commands."""

from __future__ import annotations

# The GUI launches the local pypi-profile CLI without shell=True.
import subprocess  # nosec B404
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from tkinter import filedialog, font, scrolledtext, ttk
from typing import Literal, TypedDict, cast


def _detect_keyring_status() -> str:
    """Return a short human-readable keyring status string."""
    try:
        import keyring
        import keyring.backends.fail

        backend = keyring.get_keyring()
        if isinstance(backend, keyring.backends.fail.Keyring):
            return "unavailable (disk only)"
        return f"active ({type(backend).__name__})"
    except Exception:
        return "unavailable"

ArgKind = Literal["file", "dir", "bool", "password", "choice", "str"]


class CommandArg(TypedDict, total=False):
    flag: str
    label: str
    default: str | bool
    kind: ArgKind
    choices: list[str]


class GuiCommand(TypedDict, total=False):
    name: str
    label: str
    help: str
    args: list[CommandArg]
    readonly: bool
    extra_argv: list[str]


COMMANDS: list[GuiCommand] = [
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
            "--profile-package: override the profile package name\n\n"
            "Key password: leave blank — the signing key is loaded from your system "
            "keyring automatically.  Only enter a password if you are on a system "
            "without keyring support and your key file is password-protected."
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
                "label": "Key password (keyring fallback only)",
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
    {
        "name": "update-proofs",
        "label": "Update Proofs",
        "help": (
            "Sign all [[profiles]] URLs and write stored_proof values into the TOML.\n\n"
            "This is the batch equivalent of 'Sign Claim': it iterates every entry in "
            "[[profiles]] that uses controls-url verification, signs each URL with your "
            "minisign secret key, and patches the resulting proof strings directly into "
            "pypi_profile.toml under stored_proof.\n\n"
            "After running this command, commit the updated TOML so that the static "
            "build can embed the proofs without needing your private key.\n\n"
            "Source: path to a pypi_profile.toml, a directory, or a package name.\n"
            "--profile-package: override the profile package name\n"
            "--force: re-sign URLs that already have a stored_proof\n\n"
            "Key password: leave blank — the signing key is loaded from your system "
            "keyring automatically.  Only enter a password if you are on a system "
            "without keyring support and your key file is password-protected."
        ),
        "args": [
            {
                "flag": "source",
                "label": "Source (path or package)",
                "default": "pypi_profile.toml",
                "kind": "file",
            },
            {
                "flag": "--key",
                "label": "Secret key path",
                "default": "~/.pypi_profile/minisign.key",
                "kind": "file",
            },
            {
                "flag": "--password",
                "label": "Key password (keyring fallback only)",
                "default": "",
                "kind": "password",
            },
            {
                "flag": "--profile-package",
                "label": "Profile package name override",
                "default": "",
                "kind": "str",
            },
            {
                "flag": "--force",
                "label": "Re-sign existing proofs",
                "default": False,
                "kind": "bool",
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
    "Write commands (Serve, Init, Keygen, Sign, Update Proofs) require you "
    "to fill in the arguments and press Run.\n\n"
    "Use the Browse buttons to pick files or directories interactively.\n\n"
    "Key & password:\n"
    "  Your signing key is stored in the system keyring — you do NOT need "
    "to type a password for commands that use it.  The password field is "
    "only needed on systems without keyring support (e.g. some Linux distros) "
    "when the key file on disk is password-protected."
)


class PypiProfileGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("pypi-profile GUI")
        self.geometry("1100x680")
        self.minsize(900, 500)
        self.running_proc: subprocess.Popen[str] | None = None
        self.current_cmd: GuiCommand | None = None
        self.arg_widgets: dict[str, tk.Variable] = {}

        default_key = str(Path("~/.pypi_profile/minisign.key").expanduser())
        self.global_key_path = tk.StringVar(value=default_key)
        self.global_key_password = tk.StringVar(value="")

        self.build_ui()
        self.select_command(COMMANDS[0])

    def build_ui(self) -> None:
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

        self.cmd_buttons: dict[str, tk.Button] = {}
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
                command=self.make_select_command(cmd),
            )
            btn.grid(row=i + 1, column=0, sticky="ew", padx=2, pady=1)
            left.columnconfigure(0, weight=1)
            self.cmd_buttons[cmd["name"]] = btn

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
            text="Signing Key",
            bg="#2b2b2b",
            fg="#aaaaaa",
            font=("Helvetica", 9, "bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        keyring_status = _detect_keyring_status()
        keyring_color = "#55cc55" if "unavailable" not in keyring_status else "#cc8855"
        tk.Label(
            key_frame,
            text=f"Keyring: {keyring_status}",
            bg="#2b2b2b",
            fg=keyring_color,
            font=("Helvetica", 7),
            anchor="w",
            wraplength=150,
            justify=tk.LEFT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 4))

        tk.Label(
            key_frame,
            text="Fallback path:",
            bg="#2b2b2b",
            fg="#aaaaaa",
            font=("Helvetica", 8),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(2, 0))
        key_path_entry = tk.Entry(
            key_frame,
            textvariable=self.global_key_path,
            width=16,
            font=("Courier New", 8),
            bg="#1a1a1a",
            fg="#cccccc",
            insertbackground="white",
            relief=tk.FLAT,
        )
        key_path_entry.grid(row=3, column=0, sticky="ew", pady=(0, 2))
        tk.Button(
            key_frame,
            text="…",
            font=("Helvetica", 8),
            padx=2,
            pady=0,
            command=lambda: self.global_key_path.set(
                filedialog.askopenfilename(
                    title="Select secret key",
                    filetypes=[("Key files", "*.key"), ("All files", "*.*")],
                )
                or self.global_key_path.get()
            ),
        ).grid(row=3, column=1, padx=(2, 0))

        tk.Label(
            key_frame,
            text="Password (keyring fallback only):",
            bg="#2b2b2b",
            fg="#aaaaaa",
            font=("Helvetica", 8),
            anchor="w",
            wraplength=150,
            justify=tk.LEFT,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        tk.Label(
            key_frame,
            text="Leave blank if keyring is active.",
            bg="#2b2b2b",
            fg="#777777",
            font=("Helvetica", 7),
            anchor="w",
            wraplength=150,
            justify=tk.LEFT,
        ).grid(row=5, column=0, columnspan=2, sticky="w")
        tk.Entry(
            key_frame,
            textvariable=self.global_key_password,
            show="*",
            width=16,
            font=("Courier New", 8),
            bg="#1a1a1a",
            fg="#cccccc",
            insertbackground="white",
            relief=tk.FLAT,
        ).grid(row=6, column=0, columnspan=2, sticky="ew")

        # ── CENTER panel ─────────────────────────────────────────────────
        center = tk.Frame(self)
        center.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        center.rowconfigure(0, weight=0)
        center.rowconfigure(1, weight=0)
        center.rowconfigure(2, weight=1)
        center.columnconfigure(0, weight=1)

        # Title
        self.title_var = tk.StringVar(value="")
        tk.Label(
            center,
            textvariable=self.title_var,
            font=("Helvetica", 13, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        # Args frame (scrollable via canvas for tall forms)
        args_outer = tk.Frame(center, bd=1, relief=tk.GROOVE)
        args_outer.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        args_outer.columnconfigure(0, weight=1)
        self.args_frame = args_outer

        # Output
        out_label = tk.Label(
            center, text="Output", anchor="w", font=("Helvetica", 10, "bold")
        )
        out_label.grid(row=2, column=0, sticky="w")

        self.output = scrolledtext.ScrolledText(
            center, font=mono, bg="#1e1e1e", fg="#d4d4d4", wrap=tk.WORD
        )
        self.output.grid(row=3, column=0, sticky="nsew")
        center.rowconfigure(3, weight=1)

        # Run / Stop bar
        btn_bar = tk.Frame(center)
        btn_bar.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        self.run_btn = tk.Button(
            btn_bar,
            text="Run",
            width=10,
            command=self.run_command,
            bg="#0e7c0e",
            fg="white",
        )
        self.run_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.stop_btn = tk.Button(
            btn_bar,
            text="Stop",
            width=10,
            command=self.stop_command,
            bg="#7c0e0e",
            fg="white",
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            btn_bar, textvariable=self.status_var, fg="#888888"
        )
        self.status_label.pack(side=tk.LEFT, padx=8)

        # ── RIGHT panel ──────────────────────────────────────────────────
        right = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        right.grid(row=0, column=2, sticky="nsew", padx=(0, 4), pady=4)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        tk.Label(
            right, text="Help", font=("Helvetica", 11, "bold"), anchor="w", pady=4
        ).grid(row=0, column=0, sticky="ew", padx=6)
        self.help_text = scrolledtext.ScrolledText(
            right,
            font=("Helvetica", 10),
            wrap=tk.WORD,
            bg="#f5f5f5",
            fg="#222222",
            relief=tk.FLAT,
        )
        self.help_text.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.help_text.insert(tk.END, HELP_INTRO)
        self.help_text.config(state=tk.DISABLED)

    def make_select_command(self, cmd: GuiCommand) -> Callable[[], None]:
        def select_command() -> None:
            self.select_command(cmd)

        return select_command

    def select_command(self, cmd: GuiCommand) -> None:
        self.stop_command()
        self.current_cmd = cmd

        # Highlight active button
        for name, btn in self.cmd_buttons.items():
            is_active = name == cmd["name"]
            btn.config(
                bg="#005f99" if is_active else "#2b2b2b",
                fg="white" if is_active else "#cccccc",
            )

        self.title_var.set(cmd["label"])
        self.build_args_form(cmd)
        self.update_help(cmd["help"])
        self.output.delete("1.0", tk.END)

        if cmd["readonly"]:
            self.run_btn.config(state=tk.DISABLED)
            self.run_command()
        else:
            self.run_btn.config(state=tk.NORMAL)

    def build_args_form(self, cmd: GuiCommand) -> None:
        for w in self.args_frame.winfo_children():
            w.destroy()
        self.arg_widgets.clear()

        if not cmd["args"]:
            tk.Label(
                self.args_frame, text="No arguments needed.", fg="#888888", pady=4
            ).grid(row=0, column=0, columnspan=3, padx=8)
            return

        self.args_frame.columnconfigure(1, weight=1)
        for row_i, arg in enumerate(cmd["args"]):
            label = arg["label"]
            flag = arg["flag"]
            kind = arg["kind"]
            default = arg["default"]

            tk.Label(self.args_frame, text=label + ":", anchor="e").grid(
                row=row_i, column=0, sticky="e", padx=(8, 4), pady=3
            )

            if kind == "bool":
                var: tk.Variable = tk.BooleanVar(value=bool(default))
                tk.Checkbutton(self.args_frame, variable=var).grid(
                    row=row_i, column=1, sticky="w", pady=3
                )
                self.arg_widgets[flag] = var

            elif kind == "choice":
                var = tk.StringVar(value=str(default))
                cb = ttk.Combobox(
                    self.args_frame,
                    textvariable=var,
                    values=arg["choices"],
                    state="readonly",
                    width=24,
                )
                cb.grid(row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8))
                self.arg_widgets[flag] = var

            elif kind == "password":
                var = tk.StringVar(value=str(default))
                pw_frame = tk.Frame(self.args_frame)
                pw_frame.grid(row=row_i, column=1, columnspan=2, sticky="ew", pady=3, padx=(0, 8))
                pw_frame.columnconfigure(0, weight=1)
                tk.Entry(pw_frame, textvariable=var, show="*", width=36).grid(
                    row=0, column=0, sticky="ew"
                )
                tk.Label(
                    pw_frame,
                    text="Leave blank — keyring handles this automatically.",
                    fg="#888888",
                    font=("Helvetica", 8),
                    anchor="w",
                ).grid(row=1, column=0, sticky="w")
                self.arg_widgets[flag] = var

            elif kind in ("file", "dir"):
                var = tk.StringVar(value=str(default))
                entry = tk.Entry(self.args_frame, textvariable=var, width=36)
                entry.grid(row=row_i, column=1, sticky="ew", pady=3)

                if kind == "file":

                    def browse_for_path(value_var: tk.StringVar = var) -> None:
                        if selected_path := filedialog.askopenfilename():
                            value_var.set(selected_path)

                else:

                    def browse_for_path(value_var: tk.StringVar = var) -> None:
                        if selected_path := filedialog.askdirectory():
                            value_var.set(selected_path)

                tk.Button(
                    self.args_frame, text="Browse", command=browse_for_path
                ).grid(row=row_i, column=2, padx=(4, 8), pady=3)
                self.arg_widgets[flag] = var

            else:
                var = tk.StringVar(value=str(default))
                tk.Entry(self.args_frame, textvariable=var, width=36).grid(
                    row=row_i, column=1, sticky="ew", pady=3, padx=(0, 8)
                )
                self.arg_widgets[flag] = var

    def update_help(self, text: str) -> None:
        self.help_text.config(state=tk.NORMAL)
        self.help_text.delete("1.0", tk.END)
        self.help_text.insert(tk.END, text)
        self.help_text.config(state=tk.DISABLED)

    def build_argv_and_env(self, cmd: GuiCommand) -> tuple[list[str], dict[str, str]]:
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
            var = self.arg_widgets.get(flag)
            if var is None:
                continue
            get_value = cast(Callable[[], object], var.get)
            value = get_value()

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
        key_path = self.global_key_path.get().strip()
        key_password = self.global_key_password.get().strip()
        if key_path:
            extra_env.setdefault("PYPI_PROFILE_KEY_PATH", key_path)
        if key_password:
            extra_env.setdefault("PYPI_PROFILE_KEY_PASSWORD", key_password)

        env = {**os.environ, **extra_env}
        return argv, env

    def run_command(self) -> None:
        cmd = self.current_cmd
        if cmd is None:
            return

        self.output.delete("1.0", tk.END)
        argv, env = self.build_argv_and_env(cmd)
        # Show the command without revealing env-var secrets
        self.append_output(f"$ {' '.join(argv)}\n\n")
        self.status_var.set("Running…")
        self.status_label.config(fg="#888888")
        self.run_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        def worker() -> None:
            try:
                # The GUI launches the local CLI with a fixed argv list and shell=False.
                with subprocess.Popen(  # nosec B603
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(Path.cwd()),
                    env=env,
                ) as proc:
                    self.running_proc = proc
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        self.append_output(line)
                    rc = proc.wait()
                self.running_proc = None
                self.after(0, lambda: self.on_done(rc, cmd))
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                self.append_output(f"\nERROR: {exc}\n")
                self.running_proc = None
                self.after(0, lambda: self.on_done(1, cmd))

        threading.Thread(target=worker, daemon=True).start()

    def on_done(self, rc: int, cmd: GuiCommand) -> None:
        self.stop_btn.config(state=tk.DISABLED)
        if not cmd["readonly"]:
            self.run_btn.config(state=tk.NORMAL)
        msg = f"Exited {rc}"
        self.status_var.set(msg)
        self.status_label.config(fg="#0e7c0e" if rc == 0 else "#7c0e0e")
        self.append_output(f"\n[{msg}]\n")
        self.after(5000, lambda: self.status_var.set(""))

    def stop_command(self) -> None:
        if self.running_proc is not None:
            with suppress(OSError):
                self.running_proc.terminate()
            self.running_proc = None
        self.stop_btn.config(state=tk.DISABLED)
        if self.current_cmd and not self.current_cmd["readonly"]:
            self.run_btn.config(state=tk.NORMAL)
        self.status_var.set("")
        self.status_label.config(fg="#888888")

    def append_output(self, text: str) -> None:
        def do() -> None:
            self.output.insert(tk.END, text)
            self.output.see(tk.END)

        self.after(0, do)


def main() -> None:
    app = PypiProfileGui()
    app.mainloop()


if __name__ == "__main__":
    main()
