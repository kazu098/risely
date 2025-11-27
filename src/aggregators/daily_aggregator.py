"""
日次データの集計処理
"""
import pandas as pd
from datetime import date, datetime
from typing import Dict, Optional, List
import numpy as np
from src.models.health_data import DailyHealth


class DailyAggregator:
    """日次データを集計するクラス"""
    
    def __init__(self, dataframes: Dict[str, pd.DataFrame]):
        """
        集計器を初期化
        
        パラメータ:
        - dataframes: データタイプごとのDataFrameの辞書
        """
        self.dataframes = dataframes
        
    def aggregate_sleep(self, target_date: date) -> Dict:
        """
        指定日の睡眠データを集計
        
        パラメータ:
        - target_date: 集計対象の日付
        
        戻り値:
        - 睡眠データの辞書
        """
        if 'sleep' not in self.dataframes or self.dataframes['sleep'].empty:
            return {}
        
        df = self.dataframes['sleep']
        
        # 日付でフィルタ（タイムゾーンを考慮）
        # 睡眠は前日の夜から当日の朝まで続く可能性があるため、前日の18:00から当日の18:00までを対象とする
        prev_date = target_date - pd.Timedelta(days=1)
        
        if df['start_date'].dt.tz is not None:
            tz = df['start_date'].dt.tz
            start = pd.Timestamp(datetime.combine(prev_date, datetime(1900, 1, 1, 18, 0).time()), tz=tz)
            end = pd.Timestamp(datetime.combine(target_date, datetime(1900, 1, 1, 18, 0).time()), tz=tz)
        else:
            start = pd.Timestamp(datetime.combine(prev_date, datetime(1900, 1, 1, 18, 0).time()))
            end = pd.Timestamp(datetime.combine(target_date, datetime(1900, 1, 1, 18, 0).time()))
        
        # 睡眠セッションが対象期間と重なるものを抽出
        day_sleep = df[
            (df['start_date'] < end) & 
            (df['end_date'] > start)
        ]
        
        if day_sleep.empty:
            return {}
        
        # 睡眠ステージごとに集計
        sleep_data = {
            'sleep_minutes': 0,
            'deep_sleep_minutes': 0,
            'rem_sleep_minutes': 0,
            'light_sleep_minutes': 0,
        }
        
        # 睡眠セッションを時系列でソート
        day_sleep = day_sleep.sort_values('start_date')
        
        # 重複を排除するため、セッションをマージ
        merged_sessions = []
        for _, row in day_sleep.iterrows():
            if pd.isna(row['start_date']) or pd.isna(row['end_date']):
                continue
            
            # 睡眠セッションの開始と終了を対象期間内に制限
            session_start = max(row['start_date'], start)
            session_end = min(row['end_date'], end)
            
            if session_start >= session_end:
                continue
            
            duration = (session_end - session_start).total_seconds() / 60
            
            # 異常に長い睡眠（12時間以上）は除外（unspecifiedやunknownの長いセッションを除外）
            if duration > 12 * 60:
                continue
            
            stage = row.get('stage', 'unknown')
            
            # unspecifiedやunknownのステージは、他のステージと重複している可能性があるため除外
            if stage in ['unknown', 'unspecified']:
                continue
            
            merged_sessions.append({
                'start': session_start,
                'end': session_end,
                'stage': stage,
                'duration': duration
            })
        
        # セッションを時系列でソートして重複をチェック
        merged_sessions.sort(key=lambda x: x['start'])
        
        # 重複を排除（同じ時間帯のセッションは短い方を優先、または詳細なステージを優先）
        processed_sessions = []
        for session in merged_sessions:
            # 既存のセッションと重複しているかチェック
            is_duplicate = False
            for existing in processed_sessions:
                # 時間が重複している場合
                if (session['start'] < existing['end'] and session['end'] > existing['start']):
                    # より詳細なステージ（deep, rem, light）を優先
                    if session['stage'] in ['deep', 'rem', 'light'] and existing['stage'] in ['deep', 'rem', 'light']:
                        # より長い方を採用
                        if session['duration'] > existing['duration']:
                            processed_sessions.remove(existing)
                            processed_sessions.append(session)
                        is_duplicate = True
                        break
                    elif session['stage'] in ['deep', 'rem', 'light']:
                        # 詳細なステージを優先
                        processed_sessions.remove(existing)
                        processed_sessions.append(session)
                        is_duplicate = True
                        break
                    else:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                processed_sessions.append(session)
        
        # 処理済みセッションを集計
        for session in processed_sessions:
            stage = session['stage']
            duration = session['duration']
            
            if stage == 'deep':
                sleep_data['deep_sleep_minutes'] += duration
            elif stage == 'rem':
                sleep_data['rem_sleep_minutes'] += duration
            elif stage == 'light':
                sleep_data['light_sleep_minutes'] += duration
            
            # 覚醒以外は総睡眠時間に含める
            if stage != 'awake':
                sleep_data['sleep_minutes'] += duration
        
        # 異常に長い総睡眠時間（20時間以上）は除外
        if sleep_data['sleep_minutes'] > 20 * 60:
            return {}
        
        return sleep_data
    
    def aggregate_hrv(self, target_date: date, sleep_data: Optional[Dict] = None) -> Dict:
        """
        指定日のHRVデータを集計
        
        パラメータ:
        - target_date: 集計対象の日付
        - sleep_data: 睡眠データ（深い睡眠中のHRVを抽出するために使用）
        
        戻り値:
        - HRVデータの辞書
        """
        if 'hrv' not in self.dataframes or self.dataframes['hrv'].empty:
            return {}
        
        df = self.dataframes['hrv']
        
        # 前日の夜から当日の朝まで（睡眠期間）のHRVを取得
        # 前日の22:00から当日の10:00まで
        prev_date = target_date - pd.Timedelta(days=1)
        
        # タイムゾーンを考慮
        if df['start_date'].dt.tz is not None:
            tz = df['start_date'].dt.tz
            start = pd.Timestamp(datetime.combine(prev_date, datetime(1900, 1, 1, 22, 0).time()), tz=tz)
            end = pd.Timestamp(datetime.combine(target_date, datetime(1900, 1, 1, 10, 0).time()), tz=tz)
        else:
            start = pd.Timestamp(datetime.combine(prev_date, datetime(1900, 1, 1, 22, 0).time()))
            end = pd.Timestamp(datetime.combine(target_date, datetime(1900, 1, 1, 10, 0).time()))
        
        night_hrv = df[
            (df['start_date'] >= start) & 
            (df['start_date'] < end)
        ]
        
        if night_hrv.empty:
            return {}
        
        hrv_values = night_hrv['value'].dropna()
        
        hrv_data = {
            'hrv_avg': float(hrv_values.mean()) if not hrv_values.empty else None,
            'hrv_min': float(hrv_values.min()) if not hrv_values.empty else None,
            'hrv_max': float(hrv_values.max()) if not hrv_values.empty else None,
        }
        
        # 深い睡眠中のHRVを抽出（睡眠データがある場合）
        if sleep_data and 'deep_sleep_minutes' in sleep_data and sleep_data['deep_sleep_minutes'] > 0:
            # 簡易版: 夜間HRVの後半部分を深い睡眠中のHRVと仮定
            # より正確には、睡眠データと時刻をマッチングする必要がある
            deep_sleep_hrv = hrv_values.tail(int(len(hrv_values) * 0.3))  # 後半30%
            if not deep_sleep_hrv.empty:
                hrv_data['hrv_deep_sleep_avg'] = float(deep_sleep_hrv.mean())
                hrv_data['hrv_deep_sleep_stddev'] = float(deep_sleep_hrv.std())
        
        return hrv_data
    
    def aggregate_heart_rate(self, target_date: date) -> Dict:
        """
        指定日の心拍数データを集計
        
        パラメータ:
        - target_date: 集計対象の日付
        
        戻り値:
        - 心拍数データの辞書
        """
        heart_rate_data = {}
        
        # 安静時心拍数
        if 'resting_heart_rate' in self.dataframes and not self.dataframes['resting_heart_rate'].empty:
            df = self.dataframes['resting_heart_rate']
            
            # タイムゾーンを考慮
            if df['start_date'].dt.tz is not None:
                tz = df['start_date'].dt.tz
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()), tz=tz)
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()), tz=tz)
            else:
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()))
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()))
            
            day_hr = df[
                (df['start_date'] >= start) & 
                (df['start_date'] < end)
            ]
            
            if not day_hr.empty:
                heart_rate_data['resting_heart_rate'] = int(day_hr['value'].mean())
        
        # 平均心拍数
        if 'heart_rate' in self.dataframes and not self.dataframes['heart_rate'].empty:
            df = self.dataframes['heart_rate']
            
            # タイムゾーンを考慮
            if df['start_date'].dt.tz is not None:
                tz = df['start_date'].dt.tz
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()), tz=tz)
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()), tz=tz)
            else:
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()))
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()))
            
            day_hr = df[
                (df['start_date'] >= start) & 
                (df['start_date'] < end)
            ]
            
            if not day_hr.empty:
                heart_rate_data['avg_heart_rate'] = int(day_hr['value'].mean())
        
        return heart_rate_data
    
    def aggregate_workouts(self, target_date: date) -> Dict:
        """
        指定日のワークアウトデータを集計
        
        パラメータ:
        - target_date: 集計対象の日付
        
        戻り値:
        - ワークアウトデータの辞書
        """
        workout_data = {}
        
        if 'workouts' not in self.dataframes or self.dataframes['workouts'].empty:
            return workout_data
        
        df = self.dataframes['workouts']
        
        # タイムゾーンを考慮
        if df['start_date'].dt.tz is not None:
            tz = df['start_date'].dt.tz
            start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()), tz=tz)
            end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()), tz=tz)
        else:
            start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()))
            end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()))
        
        day_workouts = df[
            (df['start_date'] >= start) & 
            (df['start_date'] < end)
        ]
        
        if not day_workouts.empty:
            # ワークアウトタイプごとに集計
            workout_data['workout_count'] = len(day_workouts)
            workout_data['total_workout_duration'] = float(day_workouts['duration'].sum()) if 'duration' in day_workouts.columns else 0
            workout_data['total_workout_energy'] = float(day_workouts['total_energy_burned'].sum()) if 'total_energy_burned' in day_workouts.columns else 0
            
            # ワークアウトタイプ別の集計
            if 'type' in day_workouts.columns:
                workout_types = day_workouts['type'].value_counts().to_dict()
                workout_data['workout_types'] = workout_types
                
                # ランニングの有無と距離
                running_workouts = day_workouts[day_workouts['type'] == 'running']
                if not running_workouts.empty:
                    workout_data['has_running'] = True
                    workout_data['running_distance'] = float(running_workouts['total_distance'].sum()) if 'total_distance' in running_workouts.columns else 0
                    workout_data['running_duration'] = float(running_workouts['duration'].sum()) if 'duration' in running_workouts.columns else 0
                else:
                    workout_data['has_running'] = False
                    workout_data['running_distance'] = 0
                    workout_data['running_duration'] = 0
        
        return workout_data
    
    def aggregate_activity(self, target_date: date) -> Dict:
        """
        指定日の活動データを集計
        
        パラメータ:
        - target_date: 集計対象の日付
        
        戻り値:
        - 活動データの辞書
        """
        activity_data = {}
        
        # 歩数
        if 'steps' in self.dataframes and not self.dataframes['steps'].empty:
            df = self.dataframes['steps']
            
            # タイムゾーンを考慮
            if df['start_date'].dt.tz is not None:
                tz = df['start_date'].dt.tz
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()), tz=tz)
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()), tz=tz)
            else:
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()))
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()))
            
            day_steps = df[
                (df['start_date'] >= start) & 
                (df['start_date'] < end)
            ]
            
            if not day_steps.empty:
                # Apple Healthの歩数データは各レコードが「その時間帯の歩数」を表している
                # ただし、同じ時間帯に複数のソース（iPhone/Apple Watch）から
                # 重複したレコードがある可能性があるため、重複を除外する
                
                # 時間帯を1分単位で分割し、重複している時間帯の最大値を使用
                from datetime import timedelta
                
                min_slots = {}
                for _, row in day_steps.iterrows():
                    current = row['start_date']
                    end = row['end_date']
                    duration_minutes = max(1, (end - current).total_seconds() / 60)
                    value_per_minute = row['value'] / duration_minutes
                    
                    # このレコードの時間帯を1分単位で分割
                    while current < end:
                        slot_key = current.floor('1min')
                        if slot_key not in min_slots:
                            min_slots[slot_key] = []
                        min_slots[slot_key].append(value_per_minute)
                        current += timedelta(minutes=1)
                
                # 各スロットの最大値を使用（重複排除）
                total_steps = 0
                for slot, values in min_slots.items():
                    total_steps += max(values)
                
                activity_data['steps'] = int(total_steps)
        
        # アクティブエネルギー
        if 'active_energy' in self.dataframes and not self.dataframes['active_energy'].empty:
            df = self.dataframes['active_energy']
            
            # タイムゾーンを考慮
            if df['start_date'].dt.tz is not None:
                tz = df['start_date'].dt.tz
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()), tz=tz)
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()), tz=tz)
            else:
                start = pd.Timestamp(datetime.combine(target_date, datetime.min.time()))
                end = pd.Timestamp(datetime.combine(target_date, datetime.max.time()))
            
            day_energy = df[
                (df['start_date'] >= start) & 
                (df['start_date'] < end)
            ]
            
            if not day_energy.empty:
                activity_data['active_energy'] = float(day_energy['value'].sum())
        
        return activity_data
    
    def aggregate_daily(self, target_date: date) -> DailyHealth:
        """
        指定日のすべてのデータを集計
        
        パラメータ:
        - target_date: 集計対象の日付
        
        戻り値:
        - DailyHealthオブジェクト
        """
        sleep_data = self.aggregate_sleep(target_date)
        hrv_data = self.aggregate_hrv(target_date, sleep_data)
        heart_rate_data = self.aggregate_heart_rate(target_date)
        activity_data = self.aggregate_activity(target_date)
        workout_data = self.aggregate_workouts(target_date)
        
        # DailyHealthオブジェクトを作成
        daily_health = DailyHealth(
            date=target_date,
            **sleep_data,
            **hrv_data,
            **heart_rate_data,
            **activity_data
        )
        
        # ワークアウトデータは別途保存（将来的にテーブルを追加）
        # 現時点ではDailyHealthモデルに含めない
        
        return daily_health
    
    def aggregate_date_range(self, start_date: date, end_date: date) -> List[DailyHealth]:
        """
        日付範囲のデータを集計
        
        パラメータ:
        - start_date: 開始日
        - end_date: 終了日
        
        戻り値:
        - DailyHealthオブジェクトのリスト
        """
        daily_health_list = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_health = self.aggregate_daily(current_date)
            daily_health_list.append(daily_health)
            current_date += pd.Timedelta(days=1)
        
        return daily_health_list

