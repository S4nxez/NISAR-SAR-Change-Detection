import os

import pytest

from irrigation_footprint import config

EARTHDATA_VARS = ("EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # load_env writes os.environ: give each test a copy so nothing leaks into the session
    environ = {k: v for k, v in os.environ.items() if k not in (*EARTHDATA_VARS, "IRRIGATION_DATA_DIR")}
    monkeypatch.setattr(os, "environ", environ)


def test_repo_root_contains_the_pipeline():
    assert (config.REPO_ROOT / "pipeline" / "pyproject.toml").is_file()


def test_data_dir_defaults_to_repo_data_and_can_be_overridden(monkeypatch, tmp_path):
    assert config.data_dir() == config.REPO_ROOT / "data"
    monkeypatch.setenv("IRRIGATION_DATA_DIR", str(tmp_path))
    assert config.data_dir() == tmp_path


def test_parse_env_file_handles_comments_quotes_and_export(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n\nEARTHDATA_USERNAME=jorge\nexport EARTHDATA_PASSWORD='p=a#ss'\nMYSQL_USER=\"root\"\nbroken line\n",
        encoding="utf-8",
    )
    assert config.parse_env_file(env) == {
        "EARTHDATA_USERNAME": "jorge",
        "EARTHDATA_PASSWORD": "p=a#ss",
        "MYSQL_USER": "root",
    }


def test_missing_env_file_is_empty(tmp_path):
    assert config.parse_env_file(tmp_path / "missing.env") == {}


def test_credentials_from_env_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("EARTHDATA_USERNAME=jorge\nEARTHDATA_PASSWORD=secret\n", encoding="utf-8")
    creds = config.earthdata_credentials(env)
    assert (creds.username, creds.password, creds.token) == ("jorge", "secret", None)


def test_environment_wins_over_env_file(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("EARTHDATA_USERNAME=from_file\nEARTHDATA_PASSWORD=file_secret\n", encoding="utf-8")
    monkeypatch.setenv("EARTHDATA_USERNAME", "from_env")
    assert config.earthdata_credentials(env).username == "from_env"


def test_token_wins_over_password(monkeypatch, tmp_path):
    monkeypatch.setenv("EARTHDATA_TOKEN", "tok")
    monkeypatch.setenv("EARTHDATA_USERNAME", "jorge")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "secret")
    creds = config.earthdata_credentials(tmp_path / "missing.env")
    assert creds.token == "tok" and creds.password is None


def test_missing_credentials_raise_without_leaking(monkeypatch, tmp_path):
    monkeypatch.setenv("EARTHDATA_PASSWORD", "only-a-password")
    with pytest.raises(config.MissingCredentialsError) as error:
        config.earthdata_credentials(tmp_path / "missing.env")
    assert "only-a-password" not in str(error.value)


def test_secrets_not_in_repr():
    creds = config.EarthdataCredentials(username="jorge", password="secret", token="tok")
    assert "secret" not in repr(creds) and "tok" not in repr(creds)
