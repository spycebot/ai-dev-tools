"""scripts/set_password.py --env-file: what `make up` writes into .env."""

from scripts.set_password import write_env_file


def test_replaces_placeholders_and_keeps_other_lines(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\n"
        "AUTH_PASSWORD_HASH='$2b$12$replace-me'\n"
        "AUTH_SECRET_KEY=replace-me\n"
        "POSTGRES_PASSWORD=card_catalog\n"
    )
    write_env_file(env, "$2b$12$abc", "key123")
    assert env.read_text() == (
        "# comment\n"
        "AUTH_PASSWORD_HASH='$2b$12$abc'\n"
        "AUTH_SECRET_KEY=key123\n"
        "POSTGRES_PASSWORD=card_catalog\n"
    )


def test_appends_missing_values_and_drops_duplicates(tmp_path):
    env = tmp_path / ".env"
    env.write_text("AUTH_SECRET_KEY=a\nAUTH_SECRET_KEY=b\n")
    write_env_file(env, "$2b$12$abc", "new")
    assert env.read_text() == "AUTH_SECRET_KEY=new\nAUTH_PASSWORD_HASH='$2b$12$abc'\n"


def test_creates_the_file(tmp_path):
    env = tmp_path / ".env"
    write_env_file(env, "h", "k")
    assert env.read_text() == "AUTH_PASSWORD_HASH='h'\nAUTH_SECRET_KEY=k\n"
