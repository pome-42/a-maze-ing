# Python template for 42

42のPython課題で、同じ静的解析設定を使うための個人用テンプレートです。

## CI

pushとpull requestでは、GitHub ActionsがPython 3.12でflake8とstrict modeの
mypyを実行します。チェック用ツールのバージョンは `pyproject.toml` で固定し、
pipは実行時に最新版へ更新します。Pythonファイルがまだ存在しない場合、mypyは
スキップされます。

`prepare_submission.sh` または関連するテストとworkflowを変更した場合は、提出準備
スクリプトのテストも実行されます。

## 提出準備

`prepare_submission.sh` は、テンプレートの管理ファイルを42の提出物から取り除く
ためのスクリプトです。通常はリポジトリのルートで、引数を付けずに実行します。

```sh
./prepare_submission.sh
```

プロジェクトの `README.md` を残す場合は、`-K` または同じ意味の
`--keep-readme` を指定します。READMEにローカル変更があっても、その内容を保持した
まま実行できます。

```sh
./prepare_submission.sh -K
# または
./prepare_submission.sh --keep-readme
```

利用できるオプションは次のとおりです。

```text
-K, --keep-readme  README.mdをローカル変更ごと保持する
-h, --help         使用方法を表示する
```

通常実行では、次のパスが削除されます。

- `.github/`
- `README.md`
- `pyproject.toml`
- `.gitignore`
- `renovate.json`
- `prepare_submission.sh`

`.github/` はローカル変更があっても削除されます。`-K` または `--keep-readme` を
指定した場合、`README.md` は削除対象とclean検査の対象から外れます。それ以外の
対象に変更、未追跡ファイル、`assume-unchanged`、または`skip-worktree`の指定がある
場合、スクリプトは削除前に停止します。必要な変更をcommitするか、未追跡ファイルも
含めて退避してから、もう一度実行してください。

削除前に、`.gitignore` の規則はリポジトリローカルの `.git/info/exclude` へ保存
されます。そのため、`.gitignore` の削除後も仮想環境や秘密情報などの作業ファイルは
無視され続けます。

### 制約

- スクリプト自身がGitに記録されている必要があります。
- linked worktreeを持つリポジトリでは実行できません。
- 複数のオプション指定とシンボリックリンク経由の実行には対応していません。
- このスクリプトはcommitや42への提出を行いません。

処理が削除途中で失敗した場合は、stderrに表示される復旧コマンドを使用して
ください。正常終了後に管理ファイルを戻す場合は、次のようにHEADから復元できます。

```sh
git restore --source=HEAD -- \
  .github README.md pyproject.toml .gitignore renovate.json prepare_submission.sh
```

README保持オプションを指定した場合、表示される復旧コマンドと削除予定には
`README.md` は含まれません。
