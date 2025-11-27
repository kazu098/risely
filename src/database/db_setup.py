"""
データベースのセットアップと操作
"""
import sqlite3
from pathlib import Path
from datetime import date
from typing import Optional
import pandas as pd
from src.models.health_data import DailyHealth


class Database:
    """SQLiteデータベースの操作クラス"""
    
    def __init__(self, db_path: str = 'data/db/risely.db'):
        """
        データベースを初期化
        
        パラメータ:
        - db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _create_tables(self):
        """テーブルを作成"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 日次の生体データテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_health (
                date DATE PRIMARY KEY,
                -- 睡眠データ
                sleep_minutes INTEGER,
                deep_sleep_minutes INTEGER,
                rem_sleep_minutes INTEGER,
                light_sleep_minutes INTEGER,
                -- HRVデータ
                hrv_avg REAL,
                hrv_deep_sleep_avg REAL,
                hrv_deep_sleep_stddev REAL,
                hrv_min REAL,
                hrv_max REAL,
                hrv_baseline REAL,
                -- 心拍数データ
                resting_heart_rate INTEGER,
                avg_heart_rate INTEGER,
                -- 活動データ
                steps INTEGER,
                active_energy REAL,
                -- 計算されたスコア
                recovery_score INTEGER,
                stress_score INTEGER,
                sleep_score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # sleep_scoreカラムが存在しない場合は追加
        cursor.execute("PRAGMA table_info(daily_health)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'sleep_score' not in columns:
            cursor.execute('ALTER TABLE daily_health ADD COLUMN sleep_score INTEGER')
        
        conn.commit()
        conn.close()
    
    def insert_daily_health(self, daily_health: DailyHealth):
        """
        日次健康データを挿入または更新
        
        パラメータ:
        - daily_health: DailyHealthオブジェクト
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_health (
                date, sleep_minutes, deep_sleep_minutes, rem_sleep_minutes, light_sleep_minutes,
                hrv_avg, hrv_deep_sleep_avg, hrv_deep_sleep_stddev, hrv_min, hrv_max, hrv_baseline,
                resting_heart_rate, avg_heart_rate,
                steps, active_energy,
                recovery_score, stress_score, sleep_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            daily_health.date,
            daily_health.sleep_minutes,
            daily_health.deep_sleep_minutes,
            daily_health.rem_sleep_minutes,
            daily_health.light_sleep_minutes,
            daily_health.hrv_avg,
            daily_health.hrv_deep_sleep_avg,
            daily_health.hrv_deep_sleep_stddev,
            daily_health.hrv_min,
            daily_health.hrv_max,
            daily_health.hrv_baseline,
            daily_health.resting_heart_rate,
            daily_health.avg_heart_rate,
            daily_health.steps,
            daily_health.active_energy,
            daily_health.recovery_score,
            daily_health.stress_score,
            daily_health.sleep_score,
        ))
        
        conn.commit()
        conn.close()
    
    def get_daily_health(self, target_date: date) -> Optional[DailyHealth]:
        """
        指定日の健康データを取得
        
        パラメータ:
        - target_date: 日付
        
        戻り値:
        - DailyHealthオブジェクト、またはNone
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM daily_health WHERE date = ?', (target_date,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        # カラム名を取得
        columns = [desc[0] for desc in cursor.description]
        
        # DailyHealthオブジェクトを作成
        data = dict(zip(columns, row))
        daily_health = DailyHealth(
            date=data['date'],
            sleep_minutes=data.get('sleep_minutes'),
            deep_sleep_minutes=data.get('deep_sleep_minutes'),
            rem_sleep_minutes=data.get('rem_sleep_minutes'),
            light_sleep_minutes=data.get('light_sleep_minutes'),
            hrv_avg=data.get('hrv_avg'),
            hrv_deep_sleep_avg=data.get('hrv_deep_sleep_avg'),
            hrv_deep_sleep_stddev=data.get('hrv_deep_sleep_stddev'),
            hrv_min=data.get('hrv_min'),
            hrv_max=data.get('hrv_max'),
            hrv_baseline=data.get('hrv_baseline'),
            resting_heart_rate=data.get('resting_heart_rate'),
            avg_heart_rate=data.get('avg_heart_rate'),
            steps=data.get('steps'),
            active_energy=data.get('active_energy'),
            recovery_score=data.get('recovery_score'),
            stress_score=data.get('stress_score'),
            sleep_score=data.get('sleep_score'),
        )
        
        return daily_health
    
    def get_all_daily_health(self, start_date: Optional[date] = None, 
                             end_date: Optional[date] = None) -> list:
        """
        すべての日次健康データを取得
        
        パラメータ:
        - start_date: 開始日（オプション）
        - end_date: 終了日（オプション）
        
        戻り値:
        - DailyHealthオブジェクトのリスト
        """
        conn = sqlite3.connect(str(self.db_path))
        
        query = 'SELECT * FROM daily_health WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY date'
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        daily_health_list = []
        for _, row in df.iterrows():
            daily_health = DailyHealth(
                date=row['date'],
                sleep_minutes=row.get('sleep_minutes'),
                deep_sleep_minutes=row.get('deep_sleep_minutes'),
                rem_sleep_minutes=row.get('rem_sleep_minutes'),
                light_sleep_minutes=row.get('light_sleep_minutes'),
                hrv_avg=row.get('hrv_avg'),
                hrv_deep_sleep_avg=row.get('hrv_deep_sleep_avg'),
                hrv_deep_sleep_stddev=row.get('hrv_deep_sleep_stddev'),
                hrv_min=row.get('hrv_min'),
                hrv_max=row.get('hrv_max'),
                hrv_baseline=row.get('hrv_baseline'),
                resting_heart_rate=row.get('resting_heart_rate'),
                avg_heart_rate=row.get('avg_heart_rate'),
                steps=row.get('steps'),
                active_energy=row.get('active_energy'),
                recovery_score=row.get('recovery_score'),
                stress_score=row.get('stress_score'),
                sleep_score=row.get('sleep_score'),
            )
            daily_health_list.append(daily_health)
        
        return daily_health_list
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        データベースの内容をDataFrameに変換
        
        戻り値:
        - DataFrame
        """
        conn = sqlite3.connect(str(self.db_path))
        df = pd.read_sql_query('SELECT * FROM daily_health ORDER BY date', conn)
        conn.close()
        
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        return df

