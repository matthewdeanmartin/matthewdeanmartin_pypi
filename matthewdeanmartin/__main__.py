"""CLI entry point: `python -m matthewdeanmartin` or `matthewdeanmartin`."""

import argparse
import json
from pathlib import Path


IDENTITY_FILE = Path(__file__).parent / "identity.json"


def load_identity() -> dict:
    with open(IDENTITY_FILE, encoding="utf-8") as f:
        return json.load(f)


# -- plain text formatter --


def fmt_header(text: str) -> str:
    bar = "=" * len(text)
    return f"\n{bar}\n{text}\n{bar}"


def show_profile(data: dict) -> None:
    subject = data.get("subject", {})
    print(fmt_header(subject.get("display_name", "Unknown")))
    if summary := subject.get("summary"):
        print(f"  {summary}")

    signals = data.get("trust_signals", {})
    if signals:
        print(fmt_header("Trust Signals"))
        for key, value in signals.items():
            label = key.replace("_", " ").title()
            print(f"  {label}: {value}")

    evidence = data.get("evidence", [])
    if evidence:
        print(fmt_header("Linked Accounts"))
        for item in evidence:
            rel = " [rel=me verified]" if item.get("rel_me") else ""
            desc = f" — {item['description']}" if item.get("description") else ""
            print(f"  {item.get('kind', 'link'):>15}: {item['url']}{rel}{desc}")

    contact = data.get("contact_policy", {})
    if contact:
        print(fmt_header("Contact Policy"))
        matrix = contact.get("matrix", {})
        for category, info in matrix.items():
            label = category.replace("_", " ").title()
            allowed = "Yes" if info.get("allowed") else "No"
            print(f"  {label}: {allowed}")
            if instructions := info.get("instructions"):
                print(f"    -> {instructions}")
            for ch in info.get("channels", []):
                print(f"    -> {ch.get('kind', 'link')}: {ch.get('address', '')}")

        security = contact.get("security", {})
        if security:
            ch = security.get("channel", {})
            print(
                f"  Security Contact: {ch.get('address', 'N/A')} ({ch.get('kind', '')})"
            )

        transparency = contact.get("transparency", {})
        if transparency:
            print(
                f"  Maintenance Status: {transparency.get('maintenance_status', 'N/A')}"
            )
            print(f"  Support Policy: {transparency.get('support_policy', 'N/A')}")
            tel = transparency.get("telemetry", {})
            if tel:
                collects = "Yes" if tel.get("collects_telemetry") else "No"
                print(f"  Collects Telemetry: {collects}")

    funding = data.get("funding", {})
    if funding:
        print(fmt_header("Funding / Sponsorship"))
        for platform, value in funding.items():
            if isinstance(value, list):
                for v in value:
                    print(f"  {platform}: {v}")
            elif value:
                print(f"  {platform}: {value}")

    continuity = data.get("continuity", {})
    if continuity:
        print(fmt_header("Continuity Plan"))
        days = continuity.get("inactivity_threshold_days", "N/A")
        print(f"  Inactivity Threshold: {days} days")
        print(f"  Handoff Policy: {continuity.get('handoff_policy', 'N/A')}")
        if notes := continuity.get("notes"):
            print(f"  Notes: {notes}")

    print(fmt_header("Package Trust Info"))
    print("  This package is published on PyPI. Its age and history are")
    print("  independently verifiable at:")
    print("    https://pypi.org/project/matthewdeanmartin/")
    print("  An old, unflagged package is itself a trust signal.")
    print()


# -- markdown formatter --


def show_markdown(data: dict) -> None:
    lines: list[str] = []

    subject = data.get("subject", {})
    lines.append(f"# {subject.get('display_name', 'Unknown')}")
    if summary := subject.get("summary"):
        lines.append(f"\n{summary}")

    signals = data.get("trust_signals", {})
    if signals:
        lines.append("\n## Trust Signals\n")
        lines.append("| Signal | Value |")
        lines.append("|--------|-------|")
        for key, value in signals.items():
            label = key.replace("_", " ").title()
            lines.append(f"| {label} | {value} |")

    evidence = data.get("evidence", [])
    if evidence:
        lines.append("\n## Linked Accounts\n")
        lines.append("| Platform | Link | Verified |")
        lines.append("|----------|------|----------|")
        for item in evidence:
            kind = item.get("kind", "link")
            url = item["url"]
            rel = "rel=me" if item.get("rel_me") else ""
            desc = item.get("description", "")
            link_text = f"[{desc or kind}]({url})" if url.startswith("http") else url
            lines.append(f"| {kind} | {link_text} | {rel} |")

    contact = data.get("contact_policy", {})
    if contact:
        lines.append("\n## Contact Policy\n")
        matrix = contact.get("matrix", {})
        lines.append("| Category | Allowed | Details |")
        lines.append("|----------|---------|---------|")
        for category, info in matrix.items():
            label = category.replace("_", " ").title()
            allowed = "Yes" if info.get("allowed") else "No"
            details = info.get("instructions", "")
            for ch in info.get("channels", []):
                addr = ch.get("address", "")
                if addr:
                    details = (
                        f"[{ch.get('kind', 'link')}]({addr})"
                        if addr.startswith("http")
                        else addr
                    )
            lines.append(f"| {label} | {allowed} | {details} |")

        security = contact.get("security", {})
        if security:
            ch = security.get("channel", {})
            lines.append(
                f"\n**Security contact:** {ch.get('address', 'N/A')} ({ch.get('kind', '')})"
            )

        transparency = contact.get("transparency", {})
        if transparency:
            lines.append(
                f"\n- **Maintenance status:** {transparency.get('maintenance_status', 'N/A')}"
            )
            lines.append(
                f"- **Support policy:** {transparency.get('support_policy', 'N/A')}"
            )
            tel = transparency.get("telemetry", {})
            if tel:
                collects = "Yes" if tel.get("collects_telemetry") else "No"
                lines.append(f"- **Collects telemetry:** {collects}")

    funding = data.get("funding", {})
    if funding:
        has_values = any(
            (isinstance(v, list) and v) or (isinstance(v, str) and v)
            for v in funding.values()
        )
        if has_values:
            lines.append("\n## Funding / Sponsorship\n")
            for platform, value in funding.items():
                if isinstance(value, list):
                    for v in value:
                        if v:
                            lines.append(f"- **{platform}:** {v}")
                elif value:
                    lines.append(f"- **{platform}:** {value}")

    continuity = data.get("continuity", {})
    if continuity:
        lines.append("\n## Continuity Plan\n")
        days = continuity.get("inactivity_threshold_days", "N/A")
        lines.append(f"- **Inactivity threshold:** {days} days")
        lines.append(f"- **Handoff policy:** {continuity.get('handoff_policy', 'N/A')}")
        if notes := continuity.get("notes"):
            lines.append(f"- **Notes:** {notes}")

    lines.append("\n## Package Trust Info\n")
    lines.append(
        "This package is published on PyPI. Its age and history are independently verifiable at:"
    )
    lines.append(
        "[pypi.org/project/matthewdeanmartin](https://pypi.org/project/matthewdeanmartin/)"
    )
    lines.append("\nAn old, unflagged package is itself a trust signal.")

    print("\n".join(lines))


# -- json formatter --


def show_json(data: dict) -> None:
    print(json.dumps(data, indent=2))


# -- CLI --


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="matthewdeanmartin",
        description="Who is matthewdeanmartin? Identity & trust info for a PyPI maintainer.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    # keep --json as a shorthand for backwards compat
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shorthand for --format json",
    )
    parser.add_argument(
        "--markdown",
        "--md",
        action="store_true",
        help="Shorthand for --format markdown",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show package version",
    )
    args = parser.parse_args(argv)

    if args.version:
        from matthewdeanmartin import __version__

        print(f"matthewdeanmartin {__version__}")
        return

    data = load_identity()

    if args.json:
        fmt = "json"
    elif args.markdown:
        fmt = "markdown"
    else:
        fmt = args.format

    if fmt == "json":
        show_json(data)
    elif fmt == "markdown":
        show_markdown(data)
    else:
        show_profile(data)


if __name__ == "__main__":
    main()
