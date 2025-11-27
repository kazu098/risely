# risely 次の実装ステップ

## 現在の状況

✅ Apple Healthデータのエクスポート完了
- `apple_health_export/export.xml` (1.9GB)
- `apple_health_export/export_cda.xml` (1.3GB)

## 必要なデータソース一覧

### 1. Apple Health（ウェアラブルデータ）✅ 取得済み
- 睡眠データ、HRV、心拍数、歩数、アクティブエネルギー
- 実装状況: エクスポート完了、パース待ち

### 2. iPhone Screen Time（スマホ利用時間）📱
- **形式**: 日単位のスクリーンショット画像
- **抽出方法**: 手動入力 or OCR（将来的）
- **重要データ**: 22:00-2:00の夜間利用時間
- 詳細は `docs/data-sources-implementation.md` を参照

### 3. Google Calendar（カレンダーデータ）📅
- **連携方法**: OAuth認証でGoogle Calendar API
- **取得データ**: 会議数、会議時間、時間帯別の密度
- 詳細は `docs/data-sources-implementation.md` を参照

### 4. Mac/PC Screen Time（PC作業データ）💻
- **連携方法**: RescueTime API連携（推奨）or 手動記録
- **取得データ**: PC利用時間、アプリ別使用時間、時間帯別の分布
- 詳細は `docs/mvp-implementation.md` を参照

---

## 次の実装ステップ（Phase 1: データ収集と可視化）

### Step 1: Apple Health XMLデータのパース（優先度：高）

**目的**: XMLファイルから必要なデータを抽出し、日次の集計値を計算する

#### 必要な実装

1. **XMLパーサーの作成**
   - Apple HealthのXML形式をパース
   - 必要なデータタイプを抽出：
     * 睡眠データ（SleepAnalysis）
     * HRV（HeartRateVariabilitySDNN）
     * 心拍数（HeartRate）
     * 歩数（StepCount）
     * アクティブエネルギー（ActiveEnergyBurned）
     * 安静時心拍数（RestingHeartRate）

2. **日次集計の実装**
   - 1日ごとにデータを集計
   * 睡眠: 総睡眠時間、深い睡眠、REM睡眠、浅い睡眠
   * HRV: 
     - 夜間平均（睡眠中のHRV平均値）
     - 深い睡眠中のHRV平均値・分散（重要：リカバリースコアの指標）
     - 最小値、最大値
     - 個人のベースラインとの比較
   * 心拍数: 平均、最小、最大、安静時心拍数
   * 歩数: 1日の合計
   * アクティブエネルギー: 1日の合計
   
3. **リカバリースコアの計算**
   - HRV（特に深い睡眠中のHRV）を主要指標として使用
   - 以下の要素を組み合わせて計算：
     * 深い睡眠中のHRV平均値（高いほど回復良好）
     * HRVのベースラインからの乖離度
     * 睡眠の質（深い睡眠の割合、総睡眠時間）
     * 安静時心拍数（低いほど回復良好）
   - スコア範囲: 0-100（例：OuraのReadiness Scoreに類似）

4. **ストレススコアの計算（日単位）**
   - HRVと心拍数を基に計算
   - 以下の要素を組み合わせ：
     * HRVの低下度（ベースラインより低い = ストレス高）
     * 心拍数の上昇度
     * 睡眠の質の低下
     * 活動量とのバランス
   - スコア範囲: 0-100（低いほどストレス低、高いほどストレス高）
   - 日単位で表示可能

#### 実装ファイル構成

```
risely/
├── scripts/
│   └── parse_apple_health.py    # XMLパーサー
├── src/
│   ├── models/
│   │   └── health_data.py        # データモデル
│   ├── parsers/
│   │   └── apple_health.py       # Apple Healthパーサー
│   └── aggregators/
│       └── daily_aggregator.py   # 日次集計
├── data/
│   └── processed/                # 処理済みデータ
└── requirements.txt
```

#### 技術スタック

* **Python 3.9+**
* **pandas**: データ処理
* **xml.etree.ElementTree**: XMLパース（標準ライブラリ）
* **dateutil**: 日付処理

---

### Step 2: データベースのセットアップと保存（優先度：高）

**目的**: パースしたデータをデータベースに保存し、後続の分析に備える

#### 必要な実装

1. **SQLiteデータベースの作成**
   - 個人検証用なのでSQLiteで十分
   - スキーマ設計（`docs/mvp-implementation.md`参照）

2. **データ保存の実装**
   - 日次の集計値をテーブルに保存
   - 重複チェックと更新ロジック

#### データベーススキーマ

```sql
-- 日次の生体データ
CREATE TABLE daily_health (
    date DATE PRIMARY KEY,
    -- 睡眠データ
    sleep_minutes INTEGER,
    deep_sleep_minutes INTEGER,
    rem_sleep_minutes INTEGER,
    light_sleep_minutes INTEGER,
    -- HRVデータ
    hrv_avg REAL,                    -- 夜間平均HRV
    hrv_deep_sleep_avg REAL,         -- 深い睡眠中のHRV平均（リカバリー指標）
    hrv_deep_sleep_stddev REAL,      -- 深い睡眠中のHRV分散
    hrv_min REAL,
    hrv_max REAL,
    hrv_baseline REAL,               -- 個人のHRVベースライン（過去30日の平均など）
    -- 心拍数データ
    resting_heart_rate INTEGER,
    avg_heart_rate INTEGER,
    -- 活動データ
    steps INTEGER,
    active_energy REAL,
    -- 計算されたスコア
    recovery_score INTEGER,          -- リカバリースコア（0-100）
    stress_score INTEGER,            -- ストレススコア（0-100、低いほどストレス低）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### Step 3: 基本的な可視化（優先度：中）

**目的**: データを視覚化して、パターンを発見する

#### 必要な実装

1. **時系列グラフの作成**
   * 睡眠時間の推移
   * HRVの推移（夜間平均、深い睡眠中のHRV）
   * リカバリースコアの推移（日単位）
   * ストレススコアの推移（日単位）
   * 歩数の推移
   * 心拍数の推移

2. **相関の可視化**
   * 睡眠時間 vs HRV
   * 深い睡眠 vs 深い睡眠中のHRV
   * リカバリースコア vs ストレススコア
   * 歩数 vs 睡眠の質
   * 日付ごとの比較

3. **リカバリー・ストレススコアの可視化**
   * 日単位のリカバリースコア（0-100）
   * 日単位のストレススコア（0-100）
   * スコアの週次・月次トレンド
   * スコアと他の指標（睡眠、活動量）の相関

#### 実装方法

* **Jupyter Notebook**で探索的分析
* または**Pythonスクリプト + matplotlib/seaborn**でグラフ生成
* 将来的にWebダッシュボードに統合

---

### Step 4: 初期インサイトの抽出（優先度：中）

**目的**: データから基本的なパターンを見つける

#### 実装内容

1. **統計的分析**
   * 平均値、中央値、標準偏差
   * 週次・月次の傾向

2. **異常値の検出**
   * HRVが異常に低い日
   * 睡眠時間が極端に短い/長い日

3. **簡単な相関分析**
   * 睡眠時間とHRVの相関
   * 歩数と睡眠の質の相関

---

## 実装の優先順位

### 今すぐ実装すべきこと（Week 1）

1. ✅ **Apple Health XMLパーサー**（Step 1）
   - XMLファイルを読み込む
   - 必要なデータタイプを抽出
   - 日次集計を実装

2. ✅ **データベースセットアップ**（Step 2）
   - SQLiteデータベースを作成
   - データを保存する

3. ✅ **基本的な可視化**（Step 3）
   - 時系列グラフを作成
   - データの傾向を確認

### 次のステップ（Week 2以降）

4. 初期インサイトの抽出（Step 4）
5. Googleカレンダー連携（Phase 2）
6. スマホ・PC利用時間の取得（Phase 3）

---

## 実装の進め方

### 1. プロジェクト構造の作成

```bash
mkdir -p scripts src/{models,parsers,aggregators} data/processed
touch requirements.txt README.md
```

### 2. 依存関係のインストール

```bash
pip install pandas matplotlib seaborn python-dateutil
```

### 3. XMLパーサーの実装

`scripts/parse_apple_health.py`を作成して、XMLファイルをパース

### 4. データベースの作成

SQLiteデータベースを作成し、スキーマを定義

### 5. データの可視化

Jupyter NotebookまたはPythonスクリプトでグラフを作成

---

## 期待される成果

このPhase 1を完了すると：

* ✅ Apple Healthデータが構造化され、分析可能な状態になる
* ✅ 日次のデータが可視化され、パターンが見えてくる
* ✅ 「この日は睡眠時間は同じなのにHRVが低いな」などの気づきが得られる
* ✅ 次のPhase（カレンダー連携、スマホ利用時間）に進む準備が整う

---

## 次のアクション

1. **XMLパーサーの実装を開始**
   - `scripts/parse_apple_health.py`を作成
   - Apple Health XMLの構造を理解
   - 必要なデータタイプを抽出

2. **データベースのセットアップ**
   - SQLiteデータベースを作成
   - スキーマを定義

3. **基本的な可視化**
   - 時系列グラフを作成
   - データの傾向を確認

