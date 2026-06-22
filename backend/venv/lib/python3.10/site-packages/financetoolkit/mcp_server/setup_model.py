"""
Finance Toolkit MCP Setup Model

Helper functions that locate and write the MCP client configuration files for
VS Code, Cursor, and Claude Desktop. Each writer reads any existing file before
writing so that unrelated server entries are never disturbed, and prompts the
user for confirmation when a ``finance-toolkit`` entry is already present.
"""

import json
import os
import pathlib
import platform
import shutil
from contextlib import suppress

from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

console = Console(stderr=True)


def print_banner() -> None:
    """Print the Finance Toolkit MCP setup wizard header."""
    body = Text()
    body.append("\nFinanceToolkit", style="bold cyan")
    body.append("  ·  ", style="dim")
    body.append("MCP Setup Wizard\n", style="bold")
    body.append("Transparent and Efficient Financial Analysis\n", style="dim")
    console.print(Panel(body, border_style="cyan", padding=(0, 2)))
    console.print()


def print_menu() -> None:
    """Print the numbered client-selection menu."""
    text = Text()
    text.append("  1  ", style="bold cyan")
    text.append("Claude Desktop\n")
    text.append("  2  ", style="bold cyan")
    text.append("Claude Code\n")
    text.append("  3  ", style="bold cyan")
    text.append("VS Code\n")
    text.append("  4  ", style="bold cyan")
    text.append("Cursor\n")
    text.append("  5  ", style="bold cyan")
    text.append("Gemini\n")
    text.append("  6  ", style="bold cyan")
    text.append("Windsurf\n\n")
    text.append("  7  ", style="yellow")
    text.append("Remove configuration\n")
    text.append("  0  ", style="dim")
    text.append("Exit", style="dim")
    console.print(
        Panel(
            text,
            title="[bold]Configure Clients[/]",
            subtitle="[dim]e.g. [cyan]13[/] for Claude Desktop + VS Code[/]",
            border_style="dim",
            padding=(1, 2),
        )
    )


def ok(message: str) -> None:
    """Print a success line."""
    console.print(f"  [green]✔[/]  {message}")


def warn(message: str) -> None:
    """Print a warning line."""
    console.print(f"  [yellow]⚠[/]  {message}")


def err(message: str) -> None:
    """Print an error line."""
    console.print(f"  [red]✘[/]  {message}")


def info(message: str) -> None:
    """Print a dim informational line."""
    console.print(f"  [dim]{message}[/]")


def get_claude_config_path() -> pathlib.Path:
    """
    Return the platform-specific path to the Claude Desktop configuration file.

    Returns:
        pathlib.Path: Absolute path to claude_desktop_config.json for the
            current operating system.
    """
    system = platform.system()
    if system == "Darwin":
        return (
            pathlib.Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if system == "Windows":
        appdata = os.environ.get("APPDATA") or str(
            pathlib.Path.home() / "AppData" / "Roaming"
        )
        return pathlib.Path(appdata) / "Claude" / "claude_desktop_config.json"
    return pathlib.Path.home() / ".config" / "claude" / "claude_desktop_config.json"


def get_claude_code_config_path() -> pathlib.Path:
    """
    Return the path to the Claude Code user-level MCP configuration file.

    Claude Code stores its user-scoped MCP server registry at
    ``~/.claude.json`` on all platforms.

    Returns:
        pathlib.Path: Absolute path to ``~/.claude.json``.
    """
    return pathlib.Path.home() / ".claude.json"


def get_gemini_config_path() -> pathlib.Path:
    """
    Return the path to the Gemini CLI MCP configuration file.

    Gemini CLI stores its MCP server registry at ``~/.gemini/settings.json``
    on all platforms.

    Returns:
        pathlib.Path: Absolute path to ``~/.gemini/settings.json``.
    """
    return pathlib.Path.home() / ".gemini" / "settings.json"


def get_windsurf_config_path() -> pathlib.Path:
    """
    Return the path to the Windsurf MCP configuration file.

    Windsurf stores its MCP server registry at
    ``~/.codeium/windsurf/mcp_config.json`` on all platforms.

    Returns:
        pathlib.Path: Absolute path to ``~/.codeium/windsurf/mcp_config.json``.
    """
    return pathlib.Path.home() / ".codeium" / "windsurf" / "mcp_config.json"


def _uvx_server_entry(api_key: str | None = None) -> dict:
    """Return the MCP server config block that invokes the server via uvx.

    The generated entry is portable: it does not depend on any locally
    installed ``financetoolkit-mcp`` binary.  Clients that do not have the
    package installed can still launch the server because uvx downloads and
    runs it on demand.

    The ``env`` block uses one of two strategies, with the API key taking
    priority when both are available:

    * **Key present** — ``FINANCIAL_MODELING_PREP_API_KEY`` is embedded
      directly in the config.  The server uses it immediately without reading
      any file.
    * **Key absent** — ``FINANCETOOLKIT_ENV_FILE`` points at the global
      Finance Toolkit ``.env`` file so the server can load the key at
      runtime without storing it in the client config.

    Returns:
        dict: Ready-to-serialise MCP server configuration dict.
    """
    env = (
        {"FINANCIAL_MODELING_PREP_API_KEY": api_key}
        if api_key
        else {"FINANCETOOLKIT_ENV_FILE": str(get_global_env_path())}
    )

    return {
        "command": "uvx",
        "args": ["--from", "financetoolkit[mcp]", "financetoolkit-mcp"],
        "env": env,
    }


# Maps the canonical --client name to
#   (config_path_fn, outer_json_key, display_name)
# Used by write_client_config_uvx() and get_skill_dest_for_client().
_CLIENT_CONFIG: dict[str, tuple] = {
    "claude-desktop": (get_claude_config_path, "mcpServers", "Claude Desktop"),
    "claude-code": (get_claude_code_config_path, "mcpServers", "Claude Code"),
    "gemini": (get_gemini_config_path, "mcpServers", "Gemini"),
    "windsurf": (get_windsurf_config_path, "mcpServers", "Windsurf"),
    # VS Code and Cursor are workspace-local; their paths are resolved at
    # call time by passing target_dir.
    "vscode": (None, "servers", "VS Code"),
    "cursor": (None, "mcpServers", "Cursor"),
}


def get_global_env_path() -> pathlib.Path:
    """
    Return the platform-specific path to the global Finance Toolkit .env file.

    The file lives inside a ``financetoolkit`` subdirectory of the platform's
    standard user-configuration directory:

    * **Windows** — ``%APPDATA%\\financetoolkit\\.env``
    * **macOS / Linux** — ``$XDG_CONFIG_HOME/financetoolkit/.env``
      (falls back to ``~/.config/financetoolkit/.env`` when the variable is
      not set)

    Returns:
        pathlib.Path: Absolute path to the global .env file.
    """
    system = platform.system()
    if system == "Windows":
        base = pathlib.Path(
            os.environ.get("APPDATA")
            or str(pathlib.Path.home() / "AppData" / "Roaming")
        )
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = pathlib.Path(xdg) if xdg else pathlib.Path.home() / ".config"
    return base / "financetoolkit" / ".env"


def get_global_cache_db_path() -> pathlib.Path:
    """
    Return the path to the global Finance Toolkit SQLite cache database.

    The cache database lives alongside the global ``.env`` file so Claude
    Desktop and other MCP clients can write to a user-owned configuration
    directory instead of the current working directory.

    Returns:
        pathlib.Path: Absolute path to ``financetoolkit_cache.db`` in the
            global Finance Toolkit config directory.
    """
    return get_global_env_path().with_name("financetoolkit_cache.db")


def write_global_env_key(api_key: str) -> bool:
    """
    Write or update ``FINANCIAL_MODELING_PREP_API_KEY`` in the global .env file.

    The file (and any missing parent directories) are created automatically if
    they do not already exist. When the key is already present it is updated
    in-place without disturbing any other entries in the file.

    Args:
        api_key (str): The API key value to write.

    Returns:
        bool: ``True`` when the key was written successfully, ``False`` when a
            filesystem error prevented the write (e.g. permission denied).
    """
    env_path = get_global_env_path()
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)

        env_key = "FINANCIAL_MODELING_PREP_API_KEY"
        env_line = f"{env_key}={api_key}\n"

        existing_lines: list[str] = []
        existing_index: int | None = None

        if env_path.exists():
            existing_lines = env_path.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
            for idx, line in enumerate(existing_lines):
                if line.strip().startswith(f"{env_key}="):
                    existing_index = idx
                    break

        if existing_index is None:
            if existing_lines and not existing_lines[-1].endswith("\n"):
                existing_lines[-1] += "\n"
            existing_lines.append(env_line)
        else:
            existing_lines[existing_index] = env_line

        env_path.write_text("".join(existing_lines), encoding="utf-8")
        ok(f"API key saved to [dim cyan]{env_path}[/]")
        return True

    except OSError as exc:
        err(f"Could not write API key to [dim cyan]{env_path}[/]: {exc}")
        return False


_ENV_KEY = "FINANCIAL_MODELING_PREP_API_KEY"


def discover_api_key() -> tuple[str, str]:
    """
    Probe all known key sources and return the first API key found together with
    a human-readable description of where it came from.

    The search order is:

    1. Global Finance Toolkit env file (``get_global_env_path()``)
    2. Local ``.env`` in the current working directory
    3. ``FINANCIAL_MODELING_PREP_API_KEY`` already set in the process environment
       (e.g. exported in the shell before running the wizard)

    Returns:
        tuple[str, str]: ``(api_key, source)`` where *source* is a short label
            such as ``"global config"`` or ``"local .env"``.  Both values are
            empty strings when the key cannot be found.
    """
    # 1. Global env file
    global_env = get_global_env_path()
    if global_env.exists():
        values = dotenv_values(global_env)
        key = values.get(_ENV_KEY, "")
        if key:
            return key, "global config"

    # 2. Local .env in cwd
    local_env = pathlib.Path.cwd() / ".env"
    if local_env.exists():
        values = dotenv_values(local_env)
        key = values.get(_ENV_KEY, "")
        if key:
            return key, f"local .env ({local_env})"

    # 3. Process environment (exported shell variable)
    key = os.environ.get(_ENV_KEY, "")
    if key:
        return key, "shell environment"

    return "", ""


def remove_global_env_key() -> None:
    """
    Delete the global Finance Toolkit .env file and remove the parent directory
    if it is left empty.
    """
    env_path = get_global_env_path()
    if not env_path.exists():
        info("Global env file not found — nothing to remove.")
        return
    env_path.unlink()
    ok(f"Deleted [dim cyan]{env_path}[/]")
    with suppress(OSError):
        env_path.parent.rmdir()  # only succeeds if the directory is now empty


def _remove_entry_from_config(
    config_path: pathlib.Path,
    outer_key: str,
    entry_key: str = "finance-toolkit",
) -> None:
    """
    Remove *entry_key* from *outer_key* inside *config_path* (a JSON file).

    If the file does not exist or the entry is absent, a short notice is printed
    and the function returns without modifying anything.

    Args:
        config_path: Absolute path to the JSON config file.
        outer_key: Top-level JSON key that contains the server map
            (``"servers"`` for VS Code, ``"mcpServers"`` for others).
        entry_key: The server entry to remove. Defaults to ``"finance-toolkit"``.
    """
    if not config_path.exists():
        info(f"No config found at {config_path} — skipping.")
        return

    existing: dict = {}
    with suppress(json.JSONDecodeError):
        existing = json.loads(config_path.read_text(encoding="utf-8"))

    if entry_key not in existing.get(outer_key, {}):
        info(f"No '{entry_key}' entry found in {config_path} — skipping.")
        return

    del existing[outer_key][entry_key]
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"Removed [bold]'{entry_key}'[/] from [dim cyan]{config_path}[/]")


def remove_vscode_config(target_dir: pathlib.Path) -> None:
    """
    Remove the ``finance-toolkit`` entry from ``.vscode/mcp.json``.

    Args:
        target_dir: Directory that contains the ``.vscode`` subdirectory.
    """
    _remove_entry_from_config(
        target_dir / ".vscode" / "mcp.json",
        outer_key="servers",
    )


def remove_cursor_config(target_dir: pathlib.Path) -> None:
    """
    Remove the ``finance-toolkit`` entry from ``.cursor/mcp.json``.

    Args:
        target_dir: Directory that contains the ``.cursor`` subdirectory.
    """
    _remove_entry_from_config(
        target_dir / ".cursor" / "mcp.json",
        outer_key="mcpServers",
    )


def remove_claude_config() -> None:
    """Remove the ``finance-toolkit`` entry from the Claude Desktop config file."""
    _remove_entry_from_config(
        get_claude_config_path(),
        outer_key="mcpServers",
    )


def remove_all_configs(target_dir: pathlib.Path) -> None:
    """
    Remove the ``finance-toolkit`` entry from every known client config file and
    delete the global Finance Toolkit .env file.

    The function prints a summary of what exists before asking for confirmation
    so the user knows exactly what will be removed.

    Args:
        target_dir: Working directory used to resolve ``.vscode`` and ``.cursor``
            paths (typically ``pathlib.Path.cwd()``).
    """
    candidates = [
        ("Claude Desktop", get_claude_config_path(), "mcpServers"),
        ("Claude Code", get_claude_code_config_path(), "mcpServers"),
        ("VS Code", target_dir / ".vscode" / "mcp.json", "servers"),
        ("Cursor", target_dir / ".cursor" / "mcp.json", "mcpServers"),
        ("Gemini", get_gemini_config_path(), "mcpServers"),
        ("Windsurf", get_windsurf_config_path(), "mcpServers"),
    ]

    found: list[tuple[str, pathlib.Path, str]] = []
    for name, path, key in candidates:
        if not path.exists():
            continue
        existing: dict = {}
        with suppress(json.JSONDecodeError):
            existing = json.loads(path.read_text(encoding="utf-8"))
        if "finance-toolkit" in existing.get(key, {}):
            found.append((name, path, key))

    global_env = get_global_env_path()
    has_global_env = global_env.exists()

    # Collect skill files installed under target_dir for all known clients.
    skill_clients = ["claude-code", "vscode", "cursor", "gemini", "windsurf"]
    skill_files_found = [
        get_skill_dest_for_client(c, target_dir)
        for c in skill_clients
        if get_skill_dest_for_client(c, target_dir).exists()
    ]
    # Deduplicate (vscode and cursor share the same path).
    seen: set[pathlib.Path] = set()
    unique_skill_files: list[pathlib.Path] = []
    for p in skill_files_found:
        if p not in seen:
            seen.add(p)
            unique_skill_files.append(p)

    if not found and not has_global_env and not unique_skill_files:
        console.print()
        info("No Finance Toolkit configuration found — nothing to remove.")
        console.print()
        return

    summary = Text()
    summary.append("The following will be removed:\n\n", style="bold")
    for name, path, _ in found:
        summary.append("  ·  ", style="yellow")
        summary.append(f"{name}  ", style="bold")
        summary.append(f"{path}\n", style="dim cyan")
    if has_global_env:
        summary.append("  ·  ", style="yellow")
        summary.append("Global env file  ", style="bold")
        summary.append(f"{global_env}\n", style="dim cyan")
    if unique_skill_files:
        if found or has_global_env:
            summary.append("\n", style="")
        summary.append("Skill files:\n", style="bold")
        for sf in unique_skill_files:
            summary.append("  ·  ", style="yellow")
            summary.append(f"{sf}\n", style="dim cyan")

    console.print()
    console.print(
        Panel(
            summary,
            title="[bold yellow]Remove Configuration[/]",
            border_style="yellow",
            padding=(1, 2),
        )
    )
    console.print()
    if not Confirm.ask("  Proceed with removal?", default=False):
        info("Removal cancelled — nothing was changed.")
        console.print()
        return

    console.print()
    for _, path, key in found:
        _remove_entry_from_config(path, outer_key=key)
    if has_global_env:
        remove_global_env_key()
    for sf in unique_skill_files:
        try:
            sf.unlink()
            ok(f"Removed skill file [dim cyan]{sf}[/]")
            # Remove the parent directory if it is now empty.
            with suppress(OSError):
                sf.parent.rmdir()
        except OSError as exc:
            err(f"Could not remove {sf}: {exc}")

    console.print()
    ok("[bold]Removal complete.[/]  Restart your client(s) to apply.")
    console.print()


def write_gemini_config(api_key: str) -> None:
    """
    Patch the Gemini CLI configuration file (``~/.gemini/settings.json``) to
    add the Finance Toolkit MCP server entry.

    When *api_key* is provided it is embedded directly as
    ``FINANCIAL_MODELING_PREP_API_KEY``; otherwise the entry uses
    ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file.

    Args:
        api_key (str): FinancialModelingPrep API key.  When non-empty the key
            is embedded directly in the config (takes priority over the env
            file).
    """
    config_path = get_gemini_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get("mcpServers", {}).get("finance-toolkit")
    if current_entry is not None:
        console.print()
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in [dim cyan]{config_path}[/]"
        )
        console.print(f"  [dim]{json.dumps(current_entry, indent=4)}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this entry?", default=False):
            info("Skipped — existing Gemini config left unchanged.")
            return

    existing.setdefault("mcpServers", {})
    existing["mcpServers"]["finance-toolkit"] = _uvx_server_entry(api_key or None)

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"Gemini config written to [dim cyan]{config_path}[/]")


def remove_gemini_config() -> None:
    """Remove the ``finance-toolkit`` entry from the Gemini CLI config file."""
    _remove_entry_from_config(
        get_gemini_config_path(),
        outer_key="mcpServers",
    )


def write_windsurf_config(api_key: str) -> None:
    """
    Patch the Windsurf configuration file
    (``~/.codeium/windsurf/mcp_config.json``) to add the Finance Toolkit MCP
    server entry.

    When *api_key* is provided it is embedded directly as
    ``FINANCIAL_MODELING_PREP_API_KEY``; otherwise the entry uses
    ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file.

    Args:
        api_key (str): FinancialModelingPrep API key.  When non-empty the key
            is embedded directly in the config (takes priority over the env
            file).
    """
    config_path = get_windsurf_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get("mcpServers", {}).get("finance-toolkit")
    if current_entry is not None:
        console.print()
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in [dim cyan]{config_path}[/]"
        )
        console.print(f"  [dim]{json.dumps(current_entry, indent=4)}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this entry?", default=False):
            info("Skipped — existing Windsurf config left unchanged.")
            return

    existing.setdefault("mcpServers", {})
    existing["mcpServers"]["finance-toolkit"] = _uvx_server_entry(api_key or None)

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"Windsurf config written to [dim cyan]{config_path}[/]")


def remove_windsurf_config() -> None:
    """Remove the ``finance-toolkit`` entry from the Windsurf config file."""
    _remove_entry_from_config(
        get_windsurf_config_path(),
        outer_key="mcpServers",
    )


def get_skill_dest_for_client(client: str, target_dir: pathlib.Path) -> pathlib.Path:
    """Return the destination path where SKILL.md should be written for *client*.

    Args:
        client: Canonical client name (``"claude-code"``, ``"vscode"``, etc.).
        target_dir: Workspace root / cwd used as the base for relative paths.

    Returns:
        pathlib.Path: Absolute path including filename.
    """
    destinations = {
        "claude-code": target_dir / ".claude" / "skills" / "finance_toolkit.md",
        "vscode": target_dir
        / ".agents"
        / "skills"
        / "finance-toolkit-analyst"
        / "SKILL.md",
        "cursor": target_dir
        / ".agents"
        / "skills"
        / "finance-toolkit-analyst"
        / "SKILL.md",
        "gemini": target_dir / ".gemini" / "skills" / "finance_toolkit.md",
        "windsurf": target_dir / ".windsurf" / "skills" / "finance_toolkit.md",
    }
    return destinations.get(client, target_dir / "SKILL.md")


def write_skill_for_client(
    client: str,
    target_dir: pathlib.Path,
    overwrite: bool = False,
) -> bool:
    """Copy the bundled SKILL.md to the correct location for *client*.

    Used by the non-interactive ``--include-skills`` CLI path.  The destination
    directory is created automatically.  When *overwrite* is ``False`` and the
    destination already exists, the function prints a warning and returns
    ``False`` without touching the file.

    Args:
        client: Canonical client name (e.g. ``"claude-code"``, ``"cursor"``).
        target_dir: Workspace root used as the base for the destination path.
        overwrite: When ``True``, silently replace an existing file.

    Returns:
        bool: ``True`` on success, ``False`` on skip or failure.
    """
    source = pathlib.Path(__file__).parent / "SKILL.md"
    if not source.exists():
        err(f"Skill source file not found at [dim cyan]{source}[/] — skipping.")
        return False

    dest = get_skill_dest_for_client(client, target_dir)

    if dest.exists() and not overwrite:
        warn(
            f"Skill file already exists at [dim cyan]{dest}[/]  — use --overwrite to replace."
        )
        return False

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        ok(f"Skill file written to [dim cyan]{dest}[/]")
        return True
    except OSError as exc:
        err(f"Failed to write skill file: {exc}")
        return False


def write_client_config_uvx(
    client: str,
    target_dir: pathlib.Path,
    overwrite: bool = False,
    api_key: str = "",
) -> None:
    """Write an MCP server config block that invokes the server via uvx.

    Used by the non-interactive ``--client`` CLI path.  The generated entry
    uses ``uvx --from financetoolkit[mcp] financetoolkit-mcp`` so it works
    without a pre-installed package.

    If the target config file does not exist it is created (along with any
    missing parent directories).  When *overwrite* is ``False`` and an
    existing ``finance-toolkit`` entry is found, the function exits with a
    warning without modifying anything.  If the config directory for a global
    client (e.g. Gemini, Windsurf) cannot be determined, the raw JSON block is
    printed to the terminal as a fallback.

    When *api_key* is supplied it is embedded directly in the config as
    ``FINANCIAL_MODELING_PREP_API_KEY``; otherwise the entry uses
    ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file.

    Args:
        client: Canonical client name — one of ``"claude-desktop"``,
            ``"claude-code"``, ``"vscode"``, ``"cursor"``, ``"gemini"``,
            ``"windsurf"``.
        target_dir: Workspace root / cwd used to resolve workspace-local paths
            (``.vscode/mcp.json``, ``.cursor/mcp.json``).
        overwrite: When ``True``, silently replace an existing entry.
        api_key: FinancialModelingPrep API key.  When non-empty the key is
            embedded directly in the config (takes priority over the env file).
    """
    entry = _uvx_server_entry(api_key or None)

    if client in ("vscode", "cursor"):
        if client == "vscode":
            config_path = target_dir / ".vscode" / "mcp.json"
            outer_key = "servers"
        else:
            config_path = target_dir / ".cursor" / "mcp.json"
            outer_key = "mcpServers"
        config_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        cfg_fn, outer_key, _ = _CLIENT_CONFIG[client]
        config_path = cfg_fn()
        if not config_path.parent.exists():
            # Parent directory doesn't exist — client is not installed.
            # Print the raw block so the user can paste it manually.
            console.print()
            warn(
                f"Config directory not found for [bold]{_CLIENT_CONFIG[client][2]}[/].  "
                "Printing the block to paste manually:"
            )
            console.print()
            block = {"mcpServers": {"finance-toolkit": entry}}
            console.print(json.dumps(block, indent=2))
            console.print()
            return
        config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get(outer_key, {}).get("finance-toolkit")
    if current_entry is not None and not overwrite:
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in "
            f"[dim cyan]{config_path}[/]  — use --overwrite to replace."
        )
        return

    existing.setdefault(outer_key, {})
    existing[outer_key]["finance-toolkit"] = entry
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    display = _CLIENT_CONFIG.get(client, (None, None, client))[2]
    ok(f"{display} config written to [dim cyan]{config_path}[/]")


def write_claude_code_config(api_key: str) -> None:
    """
    Patch the Claude Code user configuration file (``~/.claude.json``) to add
    the Finance Toolkit MCP server entry.

    When *api_key* is provided it is embedded directly as
    ``FINANCIAL_MODELING_PREP_API_KEY``; otherwise the entry uses
    ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file so that
    the key is loaded at runtime from a file outside version control.

    If the configuration file does not exist it is created from scratch. If it
    already exists and the ``finance-toolkit`` entry is present, the user is
    shown the existing entry and asked to confirm before overwriting. All other
    existing entries are always preserved.

    Args:
        api_key (str): FinancialModelingPrep API key.  When non-empty the key
            is embedded directly in the config (takes priority over the env
            file).
    """
    config_path = get_claude_code_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get("mcpServers", {}).get("finance-toolkit")
    if current_entry is not None:
        console.print()
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in [dim cyan]{config_path}[/]"
        )
        console.print(f"  [dim]{json.dumps(current_entry, indent=4)}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this entry?", default=False):
            info("Skipped — existing Claude Code config left unchanged.")
            return

    existing.setdefault("mcpServers", {})
    existing["mcpServers"]["finance-toolkit"] = _uvx_server_entry(api_key or None)

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"Claude Code config written to [dim cyan]{config_path}[/]")


def remove_claude_code_config() -> None:
    """Remove the ``finance-toolkit`` entry from the Claude Code config file."""
    _remove_entry_from_config(
        get_claude_code_config_path(),
        outer_key="mcpServers",
    )


def write_claude_skill_file(target_dir: pathlib.Path) -> bool:
    """Copy the bundled SKILL.md to ``.claude/skills/`` in the target directory.

    Claude Code looks for skill/instruction files inside the project-level
    ``.claude/skills/`` directory. The file is placed at
    ``.claude/skills/finance-toolkit-analyst.md``.

    If the file already exists the user is asked to confirm before overwriting.

    Args:
        target_dir (pathlib.Path): Workspace root directory in which
            ``.claude/skills/`` should be created.

    Returns:
        bool: True on success, False on failure.
    """
    source = pathlib.Path(__file__).parent / "SKILL.md"
    if not source.exists():
        err(f"Skill source file not found at [dim cyan]{source}[/] — skipping.")
        return False

    dest = get_skill_dest_for_client("claude-code", target_dir)

    if dest.exists():
        console.print()
        warn(f"Existing Claude skill file found at [dim cyan]{dest}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this skill file?", default=False):
            info("Skipped — existing skill file left unchanged.")
            return False

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        ok(f"Claude Code skill file written to [dim cyan]{dest}[/]")
        return True
    except OSError as exc:
        err(f"Failed to write Claude skill file: {exc}")
        return False


def write_vscode_config(api_key: str, target_dir: pathlib.Path) -> None:
    """
    Write (or merge) a .vscode/mcp.json file in the given directory.

    When *api_key* is provided it is embedded directly as
    ``FINANCIAL_MODELING_PREP_API_KEY``; otherwise the entry uses
    ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file so that
    the key is loaded at runtime from a file outside version control.

    If the file already exists and the ``finance-toolkit`` entry is present, the
    user is shown the existing entry and asked to confirm before overwriting. All
    other existing server entries are always preserved.

    Args:
        api_key (str): FinancialModelingPrep API key.  When non-empty the key
            is embedded directly in the config (takes priority over the env
            file).
        target_dir (pathlib.Path): Directory in which .vscode/mcp.json is created.
    """
    vscode_dir = target_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    config_path = vscode_dir / "mcp.json"

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get("servers", {}).get("finance-toolkit")
    if current_entry is not None:
        console.print()
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in [dim cyan]{config_path}[/]"
        )
        console.print(f"  [dim]{json.dumps(current_entry, indent=4)}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this entry?", default=False):
            info("Skipped — existing VS Code config left unchanged.")
            return

    existing.setdefault("servers", {})
    existing["servers"]["finance-toolkit"] = _uvx_server_entry(api_key or None)

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"VS Code config written to [dim cyan]{config_path}[/]")


def write_cursor_config(api_key: str, target_dir: pathlib.Path) -> None:
    """
    Write (or merge) a .cursor/mcp.json file in the given directory.

    When *api_key* is provided it is embedded directly as
    ``FINANCIAL_MODELING_PREP_API_KEY``; otherwise the entry uses
    ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file so that
    the key is loaded at runtime from a file outside version control.

    If the file already exists and the ``finance-toolkit`` entry is present, the
    user is shown the existing entry and asked to confirm before overwriting. All
    other existing server entries are always preserved.

    Args:
        api_key (str): FinancialModelingPrep API key.  When non-empty the key
            is embedded directly in the config (takes priority over the env
            file).
        target_dir (pathlib.Path): Directory in which .cursor/mcp.json is created.
    """
    cursor_dir = target_dir / ".cursor"
    cursor_dir.mkdir(exist_ok=True)
    config_path = cursor_dir / "mcp.json"

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get("mcpServers", {}).get("finance-toolkit")
    if current_entry is not None:
        console.print()
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in [dim cyan]{config_path}[/]"
        )
        console.print(f"  [dim]{json.dumps(current_entry, indent=4)}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this entry?", default=False):
            info("Skipped — existing Cursor config left unchanged.")
            return

    existing.setdefault("mcpServers", {})
    existing["mcpServers"]["finance-toolkit"] = _uvx_server_entry(api_key or None)

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"Cursor config written to [dim cyan]{config_path}[/]")


def write_claude_config(api_key: str) -> None:
    """
    Patch the Claude Desktop configuration file to add the Finance Toolkit server.

    For Claude Desktop, the API key is embedded directly in the MCP server
    environment as ``FINANCIAL_MODELING_PREP_API_KEY`` so Claude does not need
    to point at a separate .env file.

    If the configuration file does not exist it is created from scratch, including
    any missing parent directories. If it already exists and the ``finance-toolkit``
    entry is present, the user is shown the existing entry and asked to confirm
    before overwriting. All other existing server entries are always preserved.

    Args:
        api_key (str): FinancialModelingPrep API key.  When non-empty the key
            is embedded directly in the config; otherwise the entry uses
            ``FINANCETOOLKIT_ENV_FILE`` pointing at the global ``.env`` file.
    """
    config_path = get_claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        with suppress(json.JSONDecodeError):
            existing = json.loads(config_path.read_text(encoding="utf-8"))

    current_entry = existing.get("mcpServers", {}).get("finance-toolkit")
    if current_entry is not None:
        console.print()
        warn(
            f"Existing [bold]'finance-toolkit'[/] entry found in [dim cyan]{config_path}[/]"
        )
        console.print(f"  [dim]{json.dumps(current_entry, indent=4)}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this entry?", default=False):
            info("Skipped — existing Claude Desktop config left unchanged.")
            return

    existing.setdefault("mcpServers", {})
    existing["mcpServers"]["finance-toolkit"] = _uvx_server_entry(api_key)

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    ok(f"Claude Desktop config written to [dim cyan]{config_path}[/]")


def write_skill_file(target_dir: pathlib.Path) -> None:
    """Copy the bundled SKILL.md to the correct location in the target directory.

    The skill file is placed at ``.agents/skills/finance-toolkit-analyst/SKILL.md``
    relative to *target_dir*, which is the convention used by VS Code Copilot and
    Cursor for custom skill definitions.

    If the file already exists the user is asked to confirm before overwriting.
    The source file is the ``finance-toolkit-analyst/SKILL.md`` that ships with
    this package.

    Args:
        target_dir (pathlib.Path): Workspace root directory in which the skill
            file should be installed.
    """
    source = pathlib.Path(__file__).parent / "SKILL.md"
    if not source.exists():
        err(f"Skill source file not found at [dim cyan]{source}[/] — skipping.")
        return

    dest = target_dir / ".agents" / "skills" / "finance-toolkit-analyst" / "SKILL.md"

    if dest.exists():
        console.print()
        warn(f"Existing skill file found at [dim cyan]{dest}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this skill file?", default=False):
            info("Skipped — existing skill file left unchanged.")
            return

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        ok(f"Skill file written to [dim cyan]{dest}[/]")
        return True
    except OSError as exc:
        err(f"Failed to write skill file: {exc}")
        return False


def copy_skill_file_to_cwd(target_dir: pathlib.Path) -> None:
    """Copy the bundled SKILL.md to *target_dir* directly so the user can move it.

    Used as a fallback when the standard ``.agents/skills/`` path cannot be
    written, or when Claude Desktop is selected (which has no native skill
    concept).

    Args:
        target_dir (pathlib.Path): Directory to copy SKILL.md into.
    """
    source = pathlib.Path(__file__).parent / "SKILL.md"
    if not source.exists():
        err(f"Skill source file not found at [dim cyan]{source}[/] — skipping.")
        return

    dest = target_dir / "SKILL.md"
    if dest.exists():
        console.print()
        warn(f"Existing SKILL.md found at [dim cyan]{dest}[/]")
        console.print()
        if not Confirm.ask("  Overwrite this file?", default=False):
            info("Skipped — existing file left unchanged.")
            return

    shutil.copy2(source, dest)
    ok(
        f"SKILL.md copied to [dim cyan]{dest}[/]  — move it to the correct location for your client."
    )
