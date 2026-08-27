from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _ci_text() -> str:
    return CI_PATH.read_text(encoding="utf-8")


def test_ci_workflow_exists() -> None:
    assert CI_PATH.is_file()


def test_ci_runs_canonical_make_targets() -> None:
    text = _ci_text()
    assert "make backend-install" in text
    assert "make backend-check" in text
    assert "make frontend-check" in text
    assert "npm ci" in text


def test_ci_uses_verified_language_versions() -> None:
    text = _ci_text()
    assert 'python-version: "3.12"' in text
    assert 'node-version: "22"' in text


def test_ci_defaults_trading_mode_to_paper() -> None:
    text = _ci_text()
    assert "TRADING_MODE: PAPER" in text
    assert "TRADING_MODE: FULL" not in text
    assert "TRADING_MODE=FULL" not in text


def test_ci_is_read_only_and_does_not_reference_secrets() -> None:
    text = _ci_text()
    assert "contents: read" in text
    assert "${{ secrets." not in text
    assert "NEXT_PUBLIC" not in text
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        lowered = stripped.lower()
        assert "api_key" not in lowered
        assert "api_secret" not in lowered
        assert "exchange_api" not in lowered
