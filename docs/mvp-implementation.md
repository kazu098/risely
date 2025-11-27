# risely MVP実装方針

## 実装の目的

まずは**自分のデータで本当に自分が意識していないようなインサイトを与えられるか**を実験する。

**前提条件**:
* Apple Watchユーザー
* 個人での検証が目的
* 最小限の実装で価値を検証

---

## アプリ vs Webサービス：どちらを選ぶべきか

### Lifestackのアプローチ

Lifestackは**iPhone、Android、Chrome（Web）の両方を提供**しています。

### risely MVPの推奨：**Webサービスから開始**

#### 理由

1. **開発速度が速い**
   * ネイティブアプリはApp Store審査が必要
   * Webなら即座にデプロイ・修正可能
   * 実験段階では迅速なイテレーションが重要

2. **Apple Watchデータ取得の容易さ**
   * Apple Watchのデータは**Apple Health（HealthKit）**に集約される
   * Webアプリから直接HealthKitにアクセスはできないが、**iPhoneアプリを経由**する必要がある
   * ただし、MVPでは**手動エクスポート or 簡易スクリプト**で対応可能

3. **コストが低い**
   * ネイティブアプリ開発にはSwift/Objective-Cの知識が必要
   * Webなら既存のスキルセットで対応可能な可能性が高い

4. **データ分析に集中できる**
   * MVPの目的は「インサイトが出るか」の検証
   * UI/UXの完成度より、**アルゴリズムとデータ分析の精度**が重要

#### ただし、将来的には

* **Web + 簡易iPhoneアプリ（データ取得専用）**の組み合わせが現実的
* iPhoneアプリはHealthKitからデータを取得してAPIに送信するだけの最小実装
* メインのUI/UXはWebで提供

---

## MVP実装の最小構成

### Phase 1: データ収集と可視化（1-2週間）

**目的**: 自分のデータを取得し、基本的な可視化を行う

#### 必要な実装

1. **Apple Watchデータの取得**
   * **方法1（推奨）**: Apple HealthからCSVエクスポート
     * iPhoneの「ヘルスケア」アプリ → 右上のプロフィール → 「すべてのヘルスケアデータをエクスポート」
     * これを定期的に（1日1回）エクスポートしてアップロード
   * **方法2**: 簡易Pythonスクリプト + HealthKit API（将来的に）
     * 現時点では手動エクスポートで十分

2. **データパースとDB保存**
   * CSVをパースして日次の集計値を抽出
   * データベース（SQLite or PostgreSQL）に保存
   * 必要なデータ：
     * 睡眠時間、深い睡眠、HRV、心拍数、歩数、アクティブエネルギー

3. **基本的な可視化**
   * 日次の睡眠・HRV・歩数の時系列グラフ
   * これだけでも「あれ、この日は睡眠時間は同じなのにHRVが低いな」などの気づきが得られる可能性がある

#### 技術スタック（推奨）

* **バックエンド**: Python (FastAPI or Flask)
* **データベース**: SQLite（個人検証なら十分）or PostgreSQL
* **フロントエンド**: Next.js + Tailwind CSS（シンプルなダッシュボード）
* **データ分析**: Python (pandas, matplotlib, seaborn)

---

### Phase 2: カレンダーデータの統合（1週間）

**目的**: 会議密度と生体データの相関を見る

#### 必要な実装

1. **GoogleカレンダーAPI連携**
   * OAuth認証でGoogleカレンダーにアクセス
   * 1日の予定を取得
   * 会議数、会議時間、時間帯別の密度を計算

2. **データ統合**
   * 日次の生体データ + カレンダーデータを結合
   * 「会議が4件以上ある日の翌日のHRV」などの集計

3. **相関の可視化**
   * 「会議数 vs HRV」の散布図
   * 「会議時間 vs 睡眠の質」の相関

---

### Phase 3: スマホ・PC利用時間の取得（1-2週間）

**目的**: 夜スマホ・PC作業パターンと睡眠の因果関係を検証

#### 必要な実装

1. **iPhone Screen Timeデータの取得**
   * **方法1（推奨）**: iPhoneの「スクリーンタイム」から手動で確認
     * MVPでは週1回、手動で記録
     * 特に22:00-2:00の利用時間を記録
     * 将来的にはScreen Time API（iOS 13+）を使用
   * **方法2**: 簡易iPhoneアプリでScreen Time APIから取得
     * これはPhase 2以降で実装

2. **PC作業データの取得（Mac / Windows対応）**
   * **方法1（MVP推奨）**: 手動記録
     * **Mac**: 「システム設定」→「スクリーンタイム」から手動で記録
     * **Windows**: RescueTime無料版をインストールして手動で記録
     * 週1回、以下のデータを記録：
       * 1日の総利用時間
       * 22:00-2:00の利用時間（夜間PC作業）
       * 主要アプリの使用時間（Slack、メール、コードエディタ、ブラウザ）
       * 作業時間帯の分布（午前/午後/夜間）
   * **方法2（推奨・将来的）**: RescueTime API連携
     * **Windows、Mac、Linuxで利用可能**（プラットフォーム非依存）
     * **無料版で開始可能**（基本的な追跡機能）
     * **API連携には有料版が必要**（月額$9-12程度）
     * 自動でアプリ使用時間を追跡、APIでデータ取得可能
     * 詳細は「PC作業データの取得方法」セクションを参照

3. **PC作業パターンの分析**
   * **作業内容の分類**:
     * コミュニケーション（Slack、メール、Zoom）
     * コーディング（VS Code、Xcode、ターミナル）
     * ブラウジング（Safari、Chrome）
     * その他（ドキュメント作成、デザインなど）
   * **時間帯別の分析**:
     * 午前中の作業パターン
     * 午後の作業パターン
     * 夜間（22:00以降）の作業パターン

4. **因果関係の分析**
   * 「夜スマホ60分以上」の日と「60分未満」の日で睡眠の質を比較
   * 「夜PC作業60分以上」の日と「60分未満」の日で睡眠の質を比較
   * 「PC作業時間が長い日（8時間以上）」と「短い日」でHRVを比較
   * 「コミュニケーションアプリ（Slack等）の使用時間」とストレス・睡眠の質の相関
   * 統計的有意性を確認

#### PC作業データの価値

* **デスクワーカーの行動パターンを可視化**
  * スマホだけでなく、PC作業も睡眠・疲労に影響する可能性が高い
  * 特にリモートワークが多い人にとって重要
* **作業内容と疲労の関係**
  * 「Slackの使用時間が長い日は疲労が高い」
  * 「コーディング時間が長い日の翌日は深い睡眠が少ない」
  などのパターンを発見できる可能性
* **時間帯別の作業パターン**
  * 「夜間にPC作業をしている日は睡眠の質が低下」
  * 「午前中に集中作業をしている日の睡眠の質が良い」
* **プラットフォーム非依存**
  * Windows、Mac、Linuxで同じ方法でデータ取得可能
  * RescueTimeを使用することで統一的なデータ取得が可能

---

### Phase 4: パターン分析とインサイト生成（2-3週間）

**目的**: 自分が意識していないパターンを発見

#### 必要な実装

1. **個人別の回帰モデル**
   * 日次の特徴量（睡眠、HRV、会議、スマホ）と翌朝のコンディション（HRV、睡眠スコア）の関係を学習
   * シンプルな線形回帰 or ランダムフォレストから開始

2. **重みの解釈**
   * どの要因がコンディションに最も影響しているかをランキング
   * 「あなたの場合、夜スマホが最大の敵です」などのインサイト

3. **週次レポートの自動生成**
   * 「先週のあなたのパターン」を週1回生成
   * 「夜スマホが60分を超えた日の深い睡眠：平均14%低下」などの数値を提示

---

### Phase 5: アドバイス生成（1週間）

**目的**: 毎朝「今日の1つだけの行動」を提案

#### 必要な実装

1. **コンディション判定**
   * 今日の睡眠・HRV・予定から「疲労高め / 普通 / 回復」を判定

2. **LLMによるアドバイス生成**
   * OpenAI API or Anthropic APIを使用
   * プロンプト例：
     ```
     今日のコンディション: 疲労高め
     原因: 睡眠時間7時間だが深い睡眠が少ない + 昨日の会議が4件
     今日の予定: 会議3件（午後2件）
      
     上記を踏まえて、今日の1つだけの行動を提案してください。
     ```

3. **Web UIでの表示**
   * 毎朝、ダッシュボードに「Today card」を表示

---

## 実装の優先順位

### MVP最小構成（2-3週間で実現可能）

1. ✅ **Apple Watchデータの取得と可視化**（Phase 1）
2. ✅ **Googleカレンダー連携**（Phase 2）
3. ✅ **基本的な相関分析**（Phase 4の簡易版）
4. ✅ **週次レポートの生成**（Phase 4）

### 次のステップ（検証後）

5. スマホ・PC利用時間の自動取得（Phase 3）
   * RescueTime API連携（PC作業の自動追跡）
   * Screen Time API（iPhone）
6. 個人別モデルの本格実装（Phase 4）
7. LLMによるアドバイス生成（Phase 5）

---

## 技術スタックの詳細推奨

### バックエンド

```python
# FastAPI の例
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS設定（Webフロントエンドからアクセス可能に）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/health-data")
async def upload_health_data(data: HealthData):
    # Apple Health CSVをパースしてDBに保存
    pass

@app.get("/api/daily-insights")
async def get_daily_insights():
    # 今日のアドバイスを生成
    pass
```

### データベーススキーマ（簡易版）

```sql
-- 日次の生体データ
CREATE TABLE daily_health (
    date DATE PRIMARY KEY,
    sleep_minutes INTEGER,
    deep_sleep_ratio REAL,
    hrv REAL,
    resting_heart_rate INTEGER,
    steps INTEGER,
    active_energy REAL
);

-- カレンダーデータ
CREATE TABLE daily_calendar (
    date DATE PRIMARY KEY,
    total_events INTEGER,
    meeting_count INTEGER,
    total_meeting_minutes INTEGER,
    morning_meetings INTEGER,
    afternoon_meetings INTEGER
);

-- スマホ利用時間（手動入力 or 将来的に自動取得）
CREATE TABLE daily_phone_usage (
    date DATE PRIMARY KEY,
    total_minutes INTEGER,
    night_minutes INTEGER  -- 22:00-2:00
);

-- PC利用時間（手動入力 or 将来的に自動取得）
CREATE TABLE daily_pc_usage (
    date DATE PRIMARY KEY,
    total_minutes INTEGER,
    night_minutes INTEGER,  -- 22:00-2:00
    morning_minutes INTEGER,  -- 6:00-12:00
    afternoon_minutes INTEGER,  -- 12:00-18:00
    evening_minutes INTEGER,  -- 18:00-22:00
    -- 主要アプリの使用時間（手動入力 or RescueTime API）
    slack_minutes INTEGER,
    email_minutes INTEGER,
    coding_minutes INTEGER,
    browser_minutes INTEGER
);
```

### フロントエンド（Next.js）

```typescript
// pages/dashboard.tsx
export default function Dashboard() {
  const [todayInsight, setTodayInsight] = useState(null);
  const [weeklyReport, setWeeklyReport] = useState(null);

  useEffect(() => {
    // 今日のインサイトを取得
    fetch('/api/daily-insights')
      .then(res => res.json())
      .then(data => setTodayInsight(data));
  }, []);

  return (
    <div>
      <TodayCard insight={todayInsight} />
      <WeeklyReport report={weeklyReport} />
      <HealthDataChart />
    </div>
  );
}
```

---

## データ取得の実装方法（Apple Watch）

### 方法1: 手動エクスポート（MVP推奨）

1. iPhoneの「ヘルスケア」アプリを開く
2. 右上のプロフィールアイコンをタップ
3. 「すべてのヘルスケアデータをエクスポート」を選択
4. CSVファイルをダウンロード
5. Web UIからアップロード

**メリット**:
* 実装が簡単
* すぐに始められる
* データの完全性が保証される

**デメリット**:
* 手動操作が必要
* 毎日やるのは面倒

### 方法2: 簡易iPhoneアプリ（Phase 2以降）

最小限のiPhoneアプリを作成：

```swift
// HealthKitManager.swift
import HealthKit

class HealthKitManager {
    func fetchSleepData(completion: @escaping ([SleepData]) -> Void) {
        let healthStore = HKHealthStore()
        // HealthKitから睡眠データを取得
        // APIに送信
    }
}
```

**メリット**:
* 自動化できる
* 将来的に必須

**デメリット**:
* Swiftの知識が必要
* App Store審査が必要（TestFlightなら回避可能）

---

## PC作業データの取得方法（Mac / Windows対応）

### 問題点

* **MacのScreen Time**: 自動エクスポート機能がない
* **Windows**: Screen Timeに相当する標準機能がない
* **プラットフォーム非依存のソリューションが必要**

### 推奨解決策: RescueTime API連携

**RescueTimeの特徴**:
* **Windows、macOS、Linuxで利用可能**（プラットフォーム非依存）
* **無料版（Lite）と有料版（Premium）がある**
* **APIアクセス**: 有料版で利用可能（無料版では制限あり）
* 自動でアプリ使用時間を追跡
* 詳細なレポートと生産性スコアを提供

#### 実装方法

**1. ユーザーにRescueTimeをインストールしてもらう**

* **無料版で開始可能**（基本的な追跡機能は利用可能）
* **API連携には有料版が必要**（月額$9-12程度）
* MVP段階では、**無料版で手動エクスポート or 有料版でAPI連携**の選択肢を提供

**2. API連携の実装**

```python
import requests
from datetime import datetime

# RescueTime API
def fetch_rescuetime_data(api_key, date):
    """
    RescueTime APIから日次のデータを取得
    
    API Key: ユーザーがRescueTimeの設定から取得
    """
    url = "https://www.rescuetime.com/anapi/data"
    params = {
        'key': api_key,
        'format': 'json',
        'perspective': 'interval',
        'resolution_time': 'day',
        'restrict_kind': 'activity',
        'restrict_begin': date.strftime('%Y-%m-%d'),
        'restrict_end': date.strftime('%Y-%m-%d')
    }
    response = requests.get(url, params=params)
    return response.json()

# データの例
# {
#   "productivity_pulse": 85,
#   "very_productive_percentage": 45,
#   "productive_percentage": 30,
#   "neutral_percentage": 15,
#   "distracting_percentage": 10,
#   "applications": [
#     {"name": "Slack", "time": 120},  # 分
#     {"name": "VS Code", "time": 240},
#     {"name": "Chrome", "time": 180},
#     ...
#   ],
#   "categories": [
#     {"name": "Communication & Scheduling", "time": 120},
#     {"name": "Software Development", "time": 240},
#     ...
#   ]
# }

def parse_rescuetime_data(data):
    """RescueTimeのデータをriselyの形式に変換"""
    result = {
        'total_minutes': 0,
        'night_minutes': 0,  # 22:00-2:00は別途取得が必要
        'slack_minutes': 0,
        'email_minutes': 0,
        'coding_minutes': 0,
        'browser_minutes': 0,
        'productivity_pulse': data.get('productivity_pulse', 0)
    }
    
    for app in data.get('applications', []):
        app_name = app['name'].lower()
        time = app['time']
        result['total_minutes'] += time
        
        if 'slack' in app_name or 'teams' in app_name:
            result['slack_minutes'] += time
        elif 'mail' in app_name or 'outlook' in app_name or 'gmail' in app_name:
            result['email_minutes'] += time
        elif 'code' in app_name or 'xcode' in app_name or 'studio' in app_name:
            result['coding_minutes'] += time
        elif 'chrome' in app_name or 'safari' in app_name or 'firefox' in app_name:
            result['browser_minutes'] += time
    
    return result
```

**3. ユーザー認証フロー**

```
1. riselyの設定画面で「PC作業データを連携する」を選択
2. RescueTimeアカウントを作成（無料版でOK）
3. RescueTimeの設定からAPI Keyを取得（有料版が必要）
4. riselyにAPI Keyを入力
5. 自動でデータ取得開始
```

#### メリット

* **プラットフォーム非依存**: Windows、Mac、Linuxで同じ方法でデータ取得可能
* **自動化**: 手動操作不要でデータ取得
* **詳細なデータ**: アプリ別、カテゴリ別の使用時間を取得可能
* **生産性スコア**: RescueTime独自の生産性スコアも取得可能
* **公式API**: 安定したAPIが提供されている

#### デメリット・注意点

* **有料版が必要**: API連携には有料版（月額$9-12）が必要
  * **解決策**: MVP段階では無料版で手動エクスポートも選択肢として提供
* **サードパーティ依存**: RescueTimeがサービス終了するリスク
* **プライバシー**: ユーザーがRescueTimeにデータを提供することになる

#### MVP段階での対応

**段階的なアプローチ**:

1. **Phase 1（手動記録）**: 
   * Mac: Screen Timeから手動で記録
   * Windows: RescueTime無料版で手動エクスポート
   * まずは「PC作業データが価値があるか」を検証

2. **Phase 2（自動化）**:
   * 検証が成功したら、RescueTime有料版 + API連携を推奨
   * ユーザーにRescueTime有料版の導入を案内

---

### 代替案: 手動記録（MVP推奨）

**Mac**:
1. 「システム設定」→「スクリーンタイム」から手動で記録
2. 週1回、主要データをWeb UIから入力

**Windows**:
1. RescueTime無料版をインストール
2. 週1回、レポートを確認して手動で記録
3. または、RescueTime無料版からCSVエクスポート（可能な場合）

**メリット**:
* 追加コスト不要
* すぐに始められる
* プライバシーを完全にコントロール

**デメリット**:
* 手動操作が必要
* 詳細なデータ取得が難しい

---

### 将来的な拡張

* **複数のデータソース対応**:
  * RescueTime（推奨・Windows/Mac/Linux対応）
  * Timing（Mac専用、有料）
  * ManicTime（Windows専用、有料）
  * 各プラットフォームの標準機能（Screen Time、Activity Monitorなど）

* **Apple Screen Time API**:
  * 将来的にAppleがScreen Time APIを提供する可能性
  * その場合は公式APIを優先的に使用

* **Windows標準機能**:
  * Windows 11の「フォーカス時間」などの機能が拡張される可能性
  * その場合は標準機能を優先

---

## 検証の進め方

### Week 1-2: データ収集

* Apple Watchデータを毎日エクスポート
* カレンダーデータを取得
* 基本的な可視化を実装

### Week 3-4: パターン分析

* 相関分析を実施
* 「会議が多い日はHRVが低い」などの仮説を検証
* 週次レポートを生成

### Week 5-6: インサイトの検証

* 自分が意識していなかったパターンを発見できたか確認
* 例えば：
  * 「夜スマホが長い日の翌日は深い睡眠が少ない」
  * 「会議が午後に集中する日の翌日は疲労が高い」
  * 「歩数が8000歩以上の日の睡眠の質が良い」

### 検証の成功基準

* ✅ 自分が「確かにそうだ」と思えるインサイトが1つ以上得られた
* ✅ 数値で示された因果関係が体感と一致している
* ✅ 週次レポートを見て「これは使える」と感じた

---

## 次のステップ

検証が成功したら：

1. **UI/UXの改善**
   * より見やすいダッシュボード
   * モバイル対応

2. **自動化の強化**
   * iPhoneアプリでHealthKitから自動取得
   * Screen Time APIの実装

3. **アルゴリズムの改善**
   * より精度の高い個人モデル
   * 時系列分析の追加

4. **他ユーザーへの展開**
   * 認証機能の追加
   * マルチテナント対応

---

## まとめ

**MVP実装の推奨アプローチ**:

1. **Webサービスから開始**（ネイティブアプリは後回し）
2. **手動データ取得で開始**（自動化は後回し）
3. **データ分析と可視化に集中**（UI/UXの完成度は後回し）
4. **自分のデータで検証**（他ユーザー対応は後回し）

**最小構成で2-3週間、本格的な検証まで6週間程度**を想定。

まずは**「自分が意識していないパターンを見つけられるか」**を検証することが最優先。

