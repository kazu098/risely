"""
1日単位のインサイト生成
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import date, timedelta
from src.database.db_setup import Database


class DailyInsights:
    """1日単位のインサイトを生成するクラス"""
    
    def __init__(self, db: Database):
        """
        インサイト生成器を初期化
        
        パラメータ:
        - db: Databaseオブジェクト
        """
        self.db = db
    
    def get_workout_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        ワークアウトデータを取得
        
        パラメータ:
        - start_date: 開始日
        - end_date: 終了日
        
        戻り値:
        - ワークアウトデータのDataFrame
        """
        from src.parsers.apple_health import AppleHealthParser
        from pathlib import Path
        
        xml_path = Path('apple_health_export/export.xml')
        parser = AppleHealthParser(str(xml_path))
        parser.parse()
        
        workouts = parser.extract_workouts()
        df_workouts = pd.DataFrame(workouts)
        
        if df_workouts.empty:
            return pd.DataFrame()
        
        # 日付をパース
        if 'start_date' in df_workouts.columns:
            df_workouts['start_date'] = pd.to_datetime(df_workouts['start_date'])
            df_workouts['date'] = df_workouts['start_date'].dt.date
            df_workouts['duration'] = pd.to_numeric(df_workouts['duration'], errors='coerce')
            df_workouts['total_distance'] = pd.to_numeric(df_workouts['total_distance'], errors='coerce')
            df_workouts['total_energy_burned'] = pd.to_numeric(df_workouts['total_energy_burned'], errors='coerce')
        
        # 期間でフィルタ
        df_workouts = df_workouts[
            (df_workouts['date'] >= start_date) & 
            (df_workouts['date'] <= end_date)
        ]
        
        return df_workouts
    
    def analyze_high_intensity_workout_impact(self, target_date: date, days: int = 7) -> Dict[str, any]:
        """
        高負荷運動（20-25kmのランニング、20000歩以上）の影響を分析
        
        パラメータ:
        - target_date: 分析対象の日付
        - days: 分析期間（日数）
        
        戻り値:
        - 分析結果の辞書
        """
        start_date = target_date - timedelta(days=days)
        end_date = target_date
        
        # 健康データを取得
        daily_health_list = self.db.get_all_daily_health(start_date=start_date, end_date=end_date)
        
        if not daily_health_list:
            return {}
        
        # DataFrameに変換
        data = []
        for dh in daily_health_list:
            data.append({
                'date': dh.date,
                'weekday': pd.to_datetime(dh.date).day_name(),
                'sleep_minutes': dh.sleep_minutes,
                'deep_sleep_minutes': dh.deep_sleep_minutes,
                'rem_sleep_minutes': dh.rem_sleep_minutes,
                'hrv_avg': dh.hrv_avg,
                'resting_heart_rate': dh.resting_heart_rate,
                'steps': dh.steps,
                'active_energy': dh.active_energy,
                'recovery_score': dh.recovery_score,
                'sleep_score': dh.sleep_score,
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        
        # 高負荷ランニング（20000歩以上）を識別
        # 20-25kmのランニングは約20000-25000歩に相当
        df['is_long_run'] = (df['steps'] >= 20000) & (df['steps'].notna())
        
        # ワークアウトデータを取得（参考情報として）
        df_workouts = self.get_workout_data(start_date, end_date)
        
        # ランニングデータを抽出
        if not df_workouts.empty and 'type' in df_workouts.columns:
            running_workouts = df_workouts[df_workouts['type'] == 'running'].copy()
            
            if not running_workouts.empty:
                # 日付ごとに集計
                daily_running = running_workouts.groupby('date').agg({
                    'duration': 'sum',
                    'total_energy_burned': 'sum',
                }).reset_index()
                
                # 日付をdatetime型に変換
                daily_running['date'] = pd.to_datetime(daily_running['date'])
                
                # 健康データとマージ
                df = df.merge(daily_running, on='date', how='left')
                df['running_duration'] = df['duration'].fillna(0)
                df['running_energy'] = df['total_energy_burned'].fillna(0)
            else:
                df['running_duration'] = 0
                df['running_energy'] = 0
        else:
            df['running_duration'] = 0
            df['running_energy'] = 0
        
        # 高負荷ランニング日の分析
        long_run_days = df[df['is_long_run'] == True]
        normal_days = df[df['is_long_run'] == False]
        
        analysis = {
            'long_run_count': len(long_run_days),
            'normal_days_count': len(normal_days),
        }
        
        if len(long_run_days) > 0 and len(normal_days) > 0:
            # 当日の影響
            analysis['same_day'] = {
                'sleep_minutes': {
                    'long_run': long_run_days['sleep_minutes'].mean() if 'sleep_minutes' in long_run_days.columns else None,
                    'normal': normal_days['sleep_minutes'].mean() if 'sleep_minutes' in normal_days.columns else None,
                },
                'deep_sleep_minutes': {
                    'long_run': long_run_days['deep_sleep_minutes'].mean() if 'deep_sleep_minutes' in long_run_days.columns else None,
                    'normal': normal_days['deep_sleep_minutes'].mean() if 'deep_sleep_minutes' in normal_days.columns else None,
                },
                'recovery_score': {
                    'long_run': long_run_days['recovery_score'].mean() if 'recovery_score' in long_run_days.columns else None,
                    'normal': normal_days['recovery_score'].mean() if 'recovery_score' in normal_days.columns else None,
                },
                'sleep_score': {
                    'long_run': long_run_days['sleep_score'].mean() if 'sleep_score' in long_run_days.columns else None,
                    'normal': normal_days['sleep_score'].mean() if 'sleep_score' in normal_days.columns else None,
                },
            }
            
            # 翌日の影響（高負荷ランニングの翌日）
            df['next_day_sleep'] = df['sleep_minutes'].shift(-1)
            df['next_day_deep_sleep'] = df['deep_sleep_minutes'].shift(-1)
            df['next_day_recovery'] = df['recovery_score'].shift(-1)
            df['next_day_sleep_score'] = df['sleep_score'].shift(-1)
            df['next_day_hrv'] = df['hrv_avg'].shift(-1)
            
            long_run_next_day = df[df['is_long_run'] == True]
            normal_next_day = df[df['is_long_run'] == False]
            
            analysis['next_day'] = {
                'sleep_minutes': {
                    'long_run': long_run_next_day['next_day_sleep'].mean() if 'next_day_sleep' in long_run_next_day.columns else None,
                    'normal': normal_next_day['next_day_sleep'].mean() if 'next_day_sleep' in normal_next_day.columns else None,
                },
                'deep_sleep_minutes': {
                    'long_run': long_run_next_day['next_day_deep_sleep'].mean() if 'next_day_deep_sleep' in long_run_next_day.columns else None,
                    'normal': normal_next_day['next_day_deep_sleep'].mean() if 'next_day_deep_sleep' in normal_next_day.columns else None,
                },
                'recovery_score': {
                    'long_run': long_run_next_day['next_day_recovery'].mean() if 'next_day_recovery' in long_run_next_day.columns else None,
                    'normal': normal_next_day['next_day_recovery'].mean() if 'next_day_recovery' in normal_next_day.columns else None,
                },
                'sleep_score': {
                    'long_run': long_run_next_day['next_day_sleep_score'].mean() if 'next_day_sleep_score' in long_run_next_day.columns else None,
                    'normal': normal_next_day['next_day_sleep_score'].mean() if 'next_day_sleep_score' in normal_next_day.columns else None,
                },
                'hrv_avg': {
                    'long_run': long_run_next_day['next_day_hrv'].mean() if 'next_day_hrv' in long_run_next_day.columns else None,
                    'normal': normal_next_day['next_day_hrv'].mean() if 'next_day_hrv' in normal_next_day.columns else None,
                },
            }
        
        return analysis
    
    def generate_daily_summary(self, target_date: date, days: int = 7) -> str:
        """
        過去N日間の日ごとのデータを総括
        
        パラメータ:
        - target_date: 分析対象の日付
        - days: 分析期間（日数）
        
        戻り値:
        - 総括レポート文字列
        """
        start_date = target_date - timedelta(days=days-1)
        end_date = target_date
        
        # 健康データを取得
        daily_health_list = self.db.get_all_daily_health(start_date=start_date, end_date=end_date)
        
        if not daily_health_list:
            return "データが不足しているため、インサイトを生成できませんでした。"
        
        # DataFrameに変換
        data = []
        for dh in daily_health_list:
            data.append({
                'date': dh.date,
                'weekday': pd.to_datetime(dh.date).strftime('%A'),
                'sleep_minutes': dh.sleep_minutes,
                'deep_sleep_minutes': dh.deep_sleep_minutes,
                'rem_sleep_minutes': dh.rem_sleep_minutes,
                'hrv_avg': dh.hrv_avg,
                'resting_heart_rate': dh.resting_heart_rate,
                'steps': dh.steps,
                'active_energy': dh.active_energy,
                'recovery_score': dh.recovery_score,
                'sleep_score': dh.sleep_score,
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 高負荷ランニング（20000歩以上）を識別
        df['is_long_run'] = (df['steps'] >= 20000) & (df['steps'].notna())
        
        # ワークアウトデータを取得（参考情報として）
        df_workouts = self.get_workout_data(start_date, end_date)
        
        # ランニングデータを抽出
        if not df_workouts.empty and 'type' in df_workouts.columns:
            running_workouts = df_workouts[df_workouts['type'] == 'running'].copy()
            
            if not running_workouts.empty:
                # 日付ごとに集計
                daily_running = running_workouts.groupby('date').agg({
                    'duration': 'sum',
                    'total_energy_burned': 'sum',
                }).reset_index()
                
                # 日付をdatetime型に変換
                daily_running['date'] = pd.to_datetime(daily_running['date'])
                
                # 健康データとマージ
                df = df.merge(daily_running, on='date', how='left')
                df['running_duration'] = df['duration'].fillna(0)
                df['running_energy'] = df['total_energy_burned'].fillna(0)
            else:
                df['running_duration'] = 0
                df['running_energy'] = 0
        else:
            df['running_duration'] = 0
            df['running_energy'] = 0
        
        # 高負荷運動の影響を分析
        workout_analysis = self.analyze_high_intensity_workout_impact(target_date, days)
        
        # レポートを生成
        report = f"【過去{days}日間の日ごとの総括】\n\n"
        
        # 日ごとの詳細
        report += "【日ごとのデータ】\n"
        for _, row in df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d (%A)')
            sleep_hours = row['sleep_minutes'] / 60 if pd.notna(row['sleep_minutes']) else None
            deep_sleep_min = row['deep_sleep_minutes'] if pd.notna(row['deep_sleep_minutes']) else None
            recovery_score = row['recovery_score'] if pd.notna(row['recovery_score']) else None
            sleep_score = row['sleep_score'] if pd.notna(row['sleep_score']) else None
            steps = row['steps'] if pd.notna(row['steps']) else None
            is_long_run = row.get('is_long_run', False) if 'is_long_run' in row else False
            
            report += f"\n{date_str}:\n"
            if sleep_hours:
                report += f"  睡眠: {sleep_hours:.1f}時間"
                if deep_sleep_min:
                    report += f"（深い睡眠: {deep_sleep_min:.0f}分）"
                report += "\n"
            if recovery_score:
                report += f"  リカバリースコア: {recovery_score:.0f}pt"
                if sleep_score:
                    report += f", 睡眠スコア: {sleep_score:.0f}pt"
                report += "\n"
            if steps:
                report += f"  歩数: {steps:.0f}歩"
                if is_long_run:
                    report += f" (高負荷運動日)"
                report += "\n"
        
        # 高負荷運動の影響分析
        if workout_analysis and workout_analysis.get('long_run_count', 0) > 0:
            report += f"\n【高負荷運動（20000歩以上、20-25kmのランニング相当）の影響】\n"
            report += f"高負荷ランニング日: {workout_analysis['long_run_count']}日\n"
            report += f"通常日: {workout_analysis['normal_days_count']}日\n\n"
            
            if 'same_day' in workout_analysis:
                same_day = workout_analysis['same_day']
                report += "【当日の影響】\n"
                
                if same_day['sleep_minutes']['long_run'] and same_day['sleep_minutes']['normal']:
                    diff = same_day['sleep_minutes']['long_run'] - same_day['sleep_minutes']['normal']
                    report += f"  睡眠時間: 高負荷日 {same_day['sleep_minutes']['long_run']:.0f}分 vs 通常日 {same_day['sleep_minutes']['normal']:.0f}分"
                    if diff > 0:
                        report += f"（+{diff:.0f}分）\n"
                    else:
                        report += f"（{diff:.0f}分）\n"
                
                if same_day['deep_sleep_minutes']['long_run'] and same_day['deep_sleep_minutes']['normal']:
                    diff = same_day['deep_sleep_minutes']['long_run'] - same_day['deep_sleep_minutes']['normal']
                    report += f"  深い睡眠: 高負荷日 {same_day['deep_sleep_minutes']['long_run']:.0f}分 vs 通常日 {same_day['deep_sleep_minutes']['normal']:.0f}分"
                    if diff > 0:
                        report += f"（+{diff:.0f}分）\n"
                    else:
                        report += f"（{diff:.0f}分）\n"
                
                if same_day['recovery_score']['long_run'] and same_day['recovery_score']['normal']:
                    diff = same_day['recovery_score']['long_run'] - same_day['recovery_score']['normal']
                    report += f"  リカバリースコア: 高負荷日 {same_day['recovery_score']['long_run']:.0f}pt vs 通常日 {same_day['recovery_score']['normal']:.0f}pt"
                    if diff > 0:
                        report += f"（+{diff:.0f}pt）\n"
                    else:
                        report += f"（{diff:.0f}pt）\n"
            
            if 'next_day' in workout_analysis:
                next_day = workout_analysis['next_day']
                report += "\n【翌日の影響】\n"
                
                if next_day['sleep_minutes']['long_run'] and next_day['sleep_minutes']['normal']:
                    diff = next_day['sleep_minutes']['long_run'] - next_day['sleep_minutes']['normal']
                    report += f"  睡眠時間: 高負荷日の翌日 {next_day['sleep_minutes']['long_run']:.0f}分 vs 通常日の翌日 {next_day['sleep_minutes']['normal']:.0f}分"
                    if diff > 0:
                        report += f"（+{diff:.0f}分）\n"
                    else:
                        report += f"（{diff:.0f}分）\n"
                
                if next_day['deep_sleep_minutes']['long_run'] and next_day['deep_sleep_minutes']['normal']:
                    diff = next_day['deep_sleep_minutes']['long_run'] - next_day['deep_sleep_minutes']['normal']
                    report += f"  深い睡眠: 高負荷日の翌日 {next_day['deep_sleep_minutes']['long_run']:.0f}分 vs 通常日の翌日 {next_day['deep_sleep_minutes']['normal']:.0f}分"
                    if diff > 0:
                        report += f"（+{diff:.0f}分）\n"
                    else:
                        report += f"（{diff:.0f}分）\n"
                
                if next_day['recovery_score']['long_run'] and next_day['recovery_score']['normal']:
                    diff = next_day['recovery_score']['long_run'] - next_day['recovery_score']['normal']
                    report += f"  リカバリースコア: 高負荷日の翌日 {next_day['recovery_score']['long_run']:.0f}pt vs 通常日の翌日 {next_day['recovery_score']['normal']:.0f}pt"
                    if diff > 0:
                        report += f"（+{diff:.0f}pt）\n"
                    else:
                        report += f"（{diff:.0f}pt）\n"
                
                if next_day['hrv_avg']['long_run'] and next_day['hrv_avg']['normal']:
                    diff = next_day['hrv_avg']['long_run'] - next_day['hrv_avg']['normal']
                    report += f"  HRV: 高負荷日の翌日 {next_day['hrv_avg']['long_run']:.1f}ms vs 通常日の翌日 {next_day['hrv_avg']['normal']:.1f}ms"
                    if diff > 0:
                        report += f"（+{diff:.1f}ms）\n"
                    else:
                        report += f"（{diff:.1f}ms）\n"
        
        return report

