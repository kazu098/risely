# risely

ウェアラブル・カレンダー・スマホのデータから、あなた固有の生活パターンを解析し、毎朝「今日の1つだけの行動」を提案するAI。

## プロジェクト構成

```
risely/
├── docs/                    # ドキュメント
├── scripts/                 # スクリプト
├── src/                     # ソースコード
│   ├── models/             # データモデル
│   ├── parsers/            # パーサー
│   ├── aggregators/        # 集計処理
│   ├── calculators/         # スコア計算
│   └── insights/           # インサイト生成
├── data/                    # データ
│   ├── processed/          # 処理済みデータ
│   └── db/                 # データベース
├── notebooks/              # Jupyter Notebooks
└── apple_health_export/    # Apple Healthエクスポートデータ
```

## セットアップ

```bash
# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

## Phase 1: Apple Healthデータのパースと可視化

### クイックスタート

```bash
# 1. 依存関係のインストール
pip install -r requirements.txt

# 2. Apple Health XMLデータのパース
python scripts/parse_apple_health.py

# 3. データベースへのインポートとスコア計算
python scripts/import_to_db.py

# 4. 基本的な可視化
python scripts/generate_charts.py

# 5. インサイトの生成
python scripts/generate_insights.py
```

詳細は `docs/phase1-setup-guide.md` を参照してください。

## 開発状況

- [x] プロジェクト構造の作成
- [x] Apple Health XMLパーサーの実装
- [x] データベースのセットアップ
- [x] リカバリースコア・ストレススコアの計算
- [x] 基本的な可視化
- [x] インサイトの生成

