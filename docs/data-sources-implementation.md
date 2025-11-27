# risely データソース実装ガイド

## 必要なデータソース一覧

### 1. Apple Health（ウェアラブルデータ）✅ 取得済み
- 睡眠データ、HRV、心拍数、歩数、アクティブエネルギー
- 実装状況: エクスポート完了、パース待ち

### 2. iPhone Screen Time（スマホ利用時間）📱
- 日単位のスクリーンショット画像から抽出
- 特に22:00-2:00の夜間利用時間が重要

### 3. Google Calendar（カレンダーデータ）📅
- 会議数、会議時間、時間帯別の密度
- OAuth認証でAPI連携

### 4. Mac/PC Screen Time（PC作業データ）💻
- RescueTime API連携（推奨）
- または手動記録

---

## iPhone Screen Timeデータの取得（画像から抽出）

### データの形式

**日単位のスクリーンショット画像**:
- iPhoneの「スクリーンタイム」画面のスクリーンショット
- 以下の情報が含まれる：
  * 1日の総利用時間
  * アプリ別の使用時間
  * 時間帯別の利用パターン（グラフ表示）
  * 特に22:00-2:00の夜間利用時間

### 実装方法

#### 方法1: 手動入力（MVP推奨）

**手順**:
1. 毎日、iPhoneの「スクリーンタイム」画面をスクリーンショット
2. 画像をアップロード（Web UI or ローカルフォルダ）
3. 手動で主要データを入力：
   * 1日の総利用時間（分）
   * 22:00-2:00の利用時間（分）
   * 主要アプリの使用時間（Slack、メール、SNS、動画など）

**メリット**:
* すぐに始められる
* 追加ツール不要
* プライバシーを完全にコントロール

**デメリット**:
* 手動操作が必要
* 時間がかかる

#### 方法2: OCR（光学文字認識）で自動抽出（将来的）

**実装方法**:

```python
import pytesseract
from PIL import Image
import re

def extract_screen_time_from_image(image_path):
    """
    スクリーンタイムのスクリーンショットからデータを抽出
    
    パラメータ:
    - image_path: スクリーンショット画像のパス
    """
    # OCRでテキストを抽出
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang='jpn+eng')
    
    # パターンマッチングでデータを抽出
    data = {}
    
    # 1日の総利用時間を抽出（例: "8時間30分"）
    total_match = re.search(r'(\d+)時間(\d+)分', text)
    if total_match:
        hours = int(total_match.group(1))
        minutes = int(total_match.group(2))
        data['total_minutes'] = hours * 60 + minutes
    
    # 22:00-2:00の利用時間を抽出
    # （スクリーンタイムのグラフから時間帯を読み取る）
    night_match = re.search(r'夜間.*?(\d+)分', text)
    if night_match:
        data['night_minutes'] = int(night_match.group(1))
    
    # アプリ別の使用時間を抽出
    # （アプリ名と時間のリストから抽出）
    apps = {}
    app_pattern = r'([\w\s]+)\s+(\d+)時間(\d+)分'
    for match in re.finditer(app_pattern, text):
        app_name = match.group(1).strip()
        hours = int(match.group(2))
        minutes = int(match.group(3))
        apps[app_name] = hours * 60 + minutes
    
    data['apps'] = apps
    
    return data
```

**必要なライブラリ**:
```bash
pip install pytesseract pillow
# macOSの場合
brew install tesseract tesseract-lang
```

**注意点**:
* OCRの精度は画像の品質に依存
* 日本語と英語の両方に対応する必要がある
* レイアウトが変わるとパターンマッチングが失敗する可能性

#### 方法3: 画像分類 + 手動補正（ハイブリッド）

**実装方法**:
1. 画像をアップロード
2. OCRで自動抽出を試みる
3. 抽出結果を表示してユーザーが確認・修正
4. 修正後のデータを保存

**メリット**:
* 手動入力より効率的
* 精度を確保できる

---

### データベーススキーマ

```sql
-- スマホ利用時間（日単位）
CREATE TABLE daily_phone_usage (
    date DATE PRIMARY KEY,
    total_minutes INTEGER,
    night_minutes INTEGER,  -- 22:00-2:00
    screenshot_path TEXT,   -- 画像のパス（オプション）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (date) REFERENCES daily_health(date)
);

-- アプリ別の使用時間
CREATE TABLE daily_app_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    app_name TEXT,
    minutes INTEGER,
    category TEXT,  -- 'communication', 'social', 'video', 'other'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (date) REFERENCES daily_phone_usage(date),
    UNIQUE(date, app_name)
);
```

---

## Google Calendar連携

### 必要な実装

#### 1. OAuth認証のセットアップ

**手順**:
1. Google Cloud Consoleでプロジェクトを作成
2. Google Calendar APIを有効化
3. OAuth 2.0認証情報を作成
4. リダイレクトURIを設定

**実装コード例**:

```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os

# OAuth設定
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRETS_FILE = 'client_secret.json'
REDIRECT_URI = 'http://localhost:8000/oauth2callback'

def get_calendar_service():
    """Google Calendar APIサービスを取得"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            flow.redirect_uri = REDIRECT_URI
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true')
            # ユーザーに認証URLを表示
            print(f'認証URL: {authorization_url}')
            # 認証コードを取得
            code = input('認証コードを入力: ')
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        # トークンを保存
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)
```

#### 2. カレンダーデータの取得

```python
from datetime import datetime, timedelta
import pytz

def fetch_calendar_events(date, service):
    """
    指定日のカレンダーイベントを取得
    
    パラメータ:
    - date: 日付（datetime.date）
    - service: Google Calendar APIサービス
    """
    # タイムゾーンを設定
    tz = pytz.timezone('Asia/Tokyo')
    
    # 1日の開始と終了時刻
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    start = tz.localize(start).isoformat()
    end = tz.localize(end).isoformat()
    
    # イベントを取得
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    return events

def analyze_calendar_events(events):
    """
    カレンダーイベントを分析して集計値を計算
    
    パラメータ:
    - events: イベントのリスト
    """
    analysis = {
        'total_events': len(events),
        'meeting_count': 0,
        'total_meeting_minutes': 0,
        'morning_meetings': 0,  # 6:00-12:00
        'afternoon_meetings': 0,  # 12:00-18:00
        'evening_meetings': 0,  # 18:00-22:00
        'night_meetings': 0,  # 22:00-6:00
    }
    
    for event in events:
        start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
        end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date'))
        
        if not start or not end:
            continue
        
        # 時刻をパース
        start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        duration = (end_dt - start_dt).total_seconds() / 60  # 分
        
        # 会議かどうかを判定（参加者が2人以上、またはオンライン会議）
        attendees = event.get('attendees', [])
        is_meeting = (
            len(attendees) > 1 or
            'zoom' in event.get('location', '').lower() or
            'meet' in event.get('location', '').lower() or
            'teams' in event.get('location', '').lower()
        )
        
        if is_meeting:
            analysis['meeting_count'] += 1
            analysis['total_meeting_minutes'] += duration
            
            # 時間帯別の集計
            hour = start_dt.hour
            if 6 <= hour < 12:
                analysis['morning_meetings'] += 1
            elif 12 <= hour < 18:
                analysis['afternoon_meetings'] += 1
            elif 18 <= hour < 22:
                analysis['evening_meetings'] += 1
            else:
                analysis['night_meetings'] += 1
    
    return analysis
```

#### 3. データベースへの保存

```sql
-- カレンダーデータ（日単位）
CREATE TABLE daily_calendar (
    date DATE PRIMARY KEY,
    total_events INTEGER,
    meeting_count INTEGER,
    total_meeting_minutes INTEGER,
    morning_meetings INTEGER,  -- 6:00-12:00
    afternoon_meetings INTEGER,  -- 12:00-18:00
    evening_meetings INTEGER,  -- 18:00-22:00
    night_meetings INTEGER,  -- 22:00-6:00
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (date) REFERENCES daily_health(date)
);
```

---

## 実装の優先順位

### Phase 1（現在）: Apple Healthデータのパース
- ✅ Apple Health XMLパーサー
- ✅ データベースへの保存
- ✅ 基本的な可視化

### Phase 2（次）: Google Calendar連携
- Google Calendar API認証
- カレンダーデータの取得
- 会議密度の計算
- データベースへの保存

### Phase 3（その後）: Screen Timeデータの取得
- スクリーンショット画像のアップロード機能
- 手動入力 or OCR抽出
- データベースへの保存

### Phase 4（将来的）: PC作業データの取得
- RescueTime API連携
- または手動記録

---

## 必要な依存関係

```bash
# Google Calendar API
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# OCR（オプション）
pip install pytesseract pillow

# 日付処理
pip install pytz python-dateutil

# データベース
pip install sqlite3  # 標準ライブラリ
# または
pip install sqlalchemy
```

---

## データフロー

```
1. Apple Health XML → パース → daily_health テーブル
2. Google Calendar API → 取得 → 分析 → daily_calendar テーブル
3. Screen Time 画像 → OCR/手動入力 → daily_phone_usage テーブル
4. すべてのデータを結合 → 相関分析 → インサイト生成
```

---

## 注意点

### Screen Time画像データ

* **プライバシー**: 画像には個人情報が含まれる可能性がある
* **保存場所**: 画像は暗号化して保存、またはローカルのみ
* **削除**: データ抽出後は画像を削除するオプションを提供

### Google Calendar連携

* **認証**: OAuth 2.0で安全に認証
* **権限**: 読み取り専用の権限のみを要求
* **更新頻度**: 1日1回のバッチ取得で十分

### データの整合性

* **日付の統一**: すべてのデータソースで日付をUTCまたはローカルタイムゾーンで統一
* **欠損データ**: データが取得できない日はNULLを許容
* **重複チェック**: 同じ日のデータが複数回取得されないようにする

