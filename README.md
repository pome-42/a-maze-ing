## Setup

このプロジェクトでは、Python と依存関係の管理に uv を使用します。

1. uv をインストールする

uv がインストールされていない場合は、先にインストールします。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Python をインストールする

このプロジェクトで使用する Python のバージョンは `.python-version` に定義されています。

```bash
uv python install
```

3. 依存関係をインストールする

`pyproject.toml` に定義された依存関係を、`uv.lock` に固定されたバージョンに基づいてインストールします。

```bash
uv sync --locked
```

4. チェックを実行する

flake8 を実行します。

```bash
uv run flake8 .
```

mypy を実行します。

```bash
uv run mypy .
```

`uv run` を使用する場合、`.venv` を手動で有効化する必要はありません。
