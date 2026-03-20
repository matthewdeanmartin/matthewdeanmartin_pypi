import json
from pathlib import Path
from matthewdeanmartin.__main__ import load_identity, show_profile, show_markdown, show_json, main
import pytest

def test_load_identity():
    data = load_identity()
    assert "subject" in data
    assert data["subject"]["display_name"] == "Matthew Dean Martin"

def test_show_profile(capsys):
    data = load_identity()
    show_profile(data)
    captured = capsys.readouterr()
    assert "Matthew Dean Martin" in captured.out
    assert "Trust Signals" in captured.out
    assert "Linked Accounts" in captured.out

def test_show_markdown(capsys):
    data = load_identity()
    show_markdown(data)
    captured = capsys.readouterr()
    assert "# Matthew Dean Martin" in captured.out
    assert "## Trust Signals" in captured.out
    assert "## Linked Accounts" in captured.out

def test_show_json(capsys):
    data = load_identity()
    show_json(data)
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["subject"]["display_name"] == "Matthew Dean Martin"

def test_main_default(capsys):
    main([])
    captured = capsys.readouterr()
    assert "Matthew Dean Martin" in captured.out

def test_main_json(capsys):
    main(["--format", "json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["subject"]["display_name"] == "Matthew Dean Martin"

def test_main_json_shorthand(capsys):
    main(["--json"])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["subject"]["display_name"] == "Matthew Dean Martin"

def test_main_markdown(capsys):
    main(["--format", "markdown"])
    captured = capsys.readouterr()
    assert "# Matthew Dean Martin" in captured.out

def test_main_markdown_shorthand(capsys):
    main(["--markdown"])
    captured = capsys.readouterr()
    assert "# Matthew Dean Martin" in captured.out

def test_main_version(capsys):
    main(["--version"])
    captured = capsys.readouterr()
    assert "matthewdeanmartin 0.1.0" in captured.out
