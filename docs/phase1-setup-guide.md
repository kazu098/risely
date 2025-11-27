# Phase 1 実装ガイド

## 実装の流れ

Phase 1では、Apple Healthデータのみからインサイトを生成します。

### ステップ1: 依存関係のインストール

```bash
# 仮想環境の作成（推奨）
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### ステップ2: Apple Health XMLデータのパース

```bash
python scripts/parse_apple_health.py
```

**処理内容**:
- `apple_health_export/export.xml` を読み込み
- 必要なデータタイプを抽出（睡眠、HRV、心拍数、歩数、アクティブエネルギー）
- 日次データを集計
- `data/processed/daily_health.csv` に保存

**出力**:
- データの概要（レコード数、期間など）
- 集計結果の概要

### ステップ3: データベースへのインポートとスコア計算

```bash
python scripts/import_to_db.py
```

**処理内容**:
- CSVファイルを読み込み
- SQLiteデータベースに保存
- リカバリースコアとストレススコアを計算
- ベースラインを計算（過去30日の平均）

**出力**:
- データベース: `data/db/risely.db`
- スコアの統計情報

### ステップ4: 基本的な可視化

```bash
python scripts/generate_charts.py
```

**処理内容**:
- データベースからデータを読み込み
- 以下のグラフを生成:
  * 睡眠時間の推移
  * HRVの推移
  * リカバリースコア・ストレススコアの推移
  * 活動量の推移
  * データ間の相関関係

**出力**:
- `data/processed/charts/` ディレクトリにPNG画像を保存

### ステップ5: インサイトの生成

```bash
python scripts/generate_insights.py
```

**処理内容**:
- データベースからデータを読み込み
- 以下のインサイトを生成:
  * 週次パターン（曜日ごとのリカバリースコア）
  * 睡眠の質とHRVの関係
  * 活動量と回復の関係
  * 最適な睡眠時間
  * 異常値の検出

**出力**:
- コンソールにインサイトを表示
- `data/processed/weekly_insights.txt` に保存

---

## 実装された機能

### 1. データパース
- ✅ Apple Health XMLパーサー
- ✅ 日次データの集計
- ✅ 深い睡眠中のHRV抽出

### 2. データベース
- ✅ SQLiteデータベースのセットアップ
- ✅ 日次健康データの保存

### 3. スコア計算
- ✅ リカバリースコアの計算（0-100）
- ✅ ストレススコアの計算（0-100）
- ✅ ベースラインの計算

### 4. 可視化
- ✅ 睡眠時間の推移
- ✅ HRVの推移
- ✅ リカバリースコア・ストレススコアの推移
- ✅ 活動量の推移
- ✅ 相関関係の可視化

### 5. インサイト生成
- ✅ 週次パターンの検出
- ✅ 睡眠の質とHRVの関係
- ✅ 活動量と回復の関係
- ✅ 最適な睡眠時間の特定
- ✅ 異常値の検出

---

## ファイル構成

```
risely/
├── scripts/
│   ├── parse_apple_health.py      # XMLパース
│   ├── import_to_db.py            # DBインポートとスコア計算
│   ├── generate_charts.py         # 可視化
│   └── generate_insights.py      # インサイト生成
├── src/
│   ├── models/
│   │   └── health_data.py         # データモデル
│   ├── parsers/
│   │   └── apple_health.py        # Apple Healthパーサー
│   ├── aggregators/
│   │   └── daily_aggregator.py    # 日次集計
│   ├── calculators/
│   │   └── recovery_stress.py     # スコア計算
│   ├── database/
│   │   └── db_setup.py            # データベース操作
│   ├── visualization/
│   │   └── basic_charts.py        # 可視化
│   └── insights/
│       └── phase1_insights.py     # インサイト生成
├── data/
│   ├── processed/
│   │   ├── daily_health.csv       # 処理済みデータ
│   │   ├── charts/                # グラフ画像
│   │   └── weekly_insights.txt    # インサイトレポート
│   └── db/
│       └── risely.db              # SQLiteデータベース
└── apple_health_export/
    └── export.xml                 # Apple Healthエクスポート
```

---

## トラブルシューティング

### XMLファイルが大きすぎる場合

Apple Health XMLファイルは非常に大きい場合があります（1.9GBなど）。

**対処法**:
- メモリが不足する場合は、XMLファイルを分割して処理
- または、必要な期間のデータのみを抽出

### データが取得できない場合

**確認事項**:
- XMLファイルのパスが正しいか
- データタイプの識別子が正しいか
- 日付の範囲が適切か

### スコアが計算されない場合

**確認事項**:
- 必要なデータ（HRV、睡眠、心拍数）が存在するか
- ベースラインが計算できているか（最低30日分のデータが必要）

---

## 次のステップ

Phase 1が完了したら：

1. **生成されたインサイトを確認**
   - `data/processed/weekly_insights.txt` を確認
   - グラフを確認（`data/processed/charts/`）

2. **インサイトの検証**
   - 自分が「確かにそうだ」と思えるインサイトがあるか
   - 数値で示された因果関係が体感と一致しているか

3. **Phase 2への準備**
   - Google Calendar連携の実装
   - スマホ・PC利用時間の取得

