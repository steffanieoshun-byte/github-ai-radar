import os

from app.config import load_local_env


def test_load_local_env_handles_utf8_bom(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("\ufeffGITHUB_TOKEN=token-from-bom-file\n", encoding="utf-8")

    load_local_env(env_file)

    assert os.getenv("GITHUB_TOKEN") == "token-from-bom-file"
