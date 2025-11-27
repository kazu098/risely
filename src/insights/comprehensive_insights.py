"""
包括的なインサイト生成
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import date, timedelta
from src.database.db_setup import Database


class ComprehensiveInsights:
    """包括的なインサイトを生成するクラス"""
    
    def __init__(self, db: Database):
        """
        インサイト生成器を初期化
        
        パラメータ:
        - db: Databaseオブジェクト
        """
        self.db = db
    
    def get_workout_data(self, start_date: date, end_date: date) -> pd.DataFrame:
        """ワークアウトデータを取得"""
        from src.parsers.apple_health import AppleHealthParser
        from pathlib import Path
        
        xml_path = Path('apple_health_export/export.xml')
        parser = AppleHealthParser(str(xml_path))
        parser.parse()
        
        workouts = parser.extract_workouts()
        df_workouts = pd.DataFrame(workouts)
        
        if df_workouts.empty:
            return pd.DataFrame()
        
        if 'start_date' in df_workouts.columns:
            df_workouts['start_date'] = pd.to_datetime(df_workouts['start_date'])
            df_workouts['date'] = df_workouts['start_date'].dt.date
            df_workouts['duration'] = pd.to_numeric(df_workouts['duration'], errors='coerce')
            df_workouts['total_energy_burned'] = pd.to_numeric(df_workouts['total_energy_burned'], errors='coerce')
        
        df_workouts = df_workouts[
            (df_workouts['date'] >= start_date) & 
            (df_workouts['date'] <= end_date)
        ]
        
        return df_workouts
    
    def analyze_comprehensive(self, target_date: date, days: int = 7) -> str:
        """
        包括的な分析を実行
        
        パラメータ:
        - target_date: 分析対象の日付
        - days: 分析期間（日数）
        
        戻り値:
        - 分析レポート文字列
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
                'weekday_jp': ['月', '火', '水', '木', '金', '土', '日'][pd.to_datetime(dh.date).weekday()],
                'sleep_minutes': dh.sleep_minutes,
                'deep_sleep_minutes': dh.deep_sleep_minutes,
                'rem_sleep_minutes': dh.rem_sleep_minutes,
                'light_sleep_minutes': dh.light_sleep_minutes,
                'hrv_avg': dh.hrv_avg,
                'hrv_baseline': dh.hrv_baseline,
                'resting_heart_rate': dh.resting_heart_rate,
                'steps': dh.steps,
                'active_energy': dh.active_energy,
                'recovery_score': dh.recovery_score,
                'stress_score': dh.stress_score,
                'sleep_score': dh.sleep_score,
            })
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # ワークアウトデータを取得
        df_workouts = self.get_workout_data(start_date, end_date)
        
        # ランニングデータを抽出
        if not df_workouts.empty and 'type' in df_workouts.columns:
            running_workouts = df_workouts[df_workouts['type'] == 'running'].copy()
            if not running_workouts.empty:
                daily_running = running_workouts.groupby('date').agg({
                    'duration': 'sum',
                    'total_energy_burned': 'sum',
                }).reset_index()
                daily_running['date'] = pd.to_datetime(daily_running['date'])
                df = df.merge(daily_running, on='date', how='left')
                df['running_duration'] = df['duration'].fillna(0)
                df['running_energy'] = df['total_energy_burned'].fillna(0)
            else:
                df['running_duration'] = 0
                df['running_energy'] = 0
        else:
            df['running_duration'] = 0
            df['running_energy'] = 0
        
        # 高負荷運動を識別
        df['is_long_run'] = (df['steps'] >= 20000) & (df['steps'].notna())
        
        # 計算フィールドを追加
        df['sleep_hours'] = df['sleep_minutes'] / 60 if 'sleep_minutes' in df.columns else None
        df['deep_sleep_ratio'] = (df['deep_sleep_minutes'] / df['sleep_minutes'] * 100) if 'deep_sleep_minutes' in df.columns and 'sleep_minutes' in df.columns else None
        
        # 前日・翌日のデータを追加
        df['prev_day_sleep'] = df['sleep_minutes'].shift(1)
        df['prev_day_deep_sleep'] = df['deep_sleep_minutes'].shift(1)
        df['prev_day_steps'] = df['steps'].shift(1)
        df['prev_day_active_energy'] = df['active_energy'].shift(1)
        df['next_day_recovery'] = df['recovery_score'].shift(-1)
        df['next_day_sleep'] = df['sleep_minutes'].shift(-1)
        df['next_day_deep_sleep'] = df['deep_sleep_minutes'].shift(-1)
        df['next_day_hrv'] = df['hrv_avg'].shift(-1)
        df['next_day_sleep_score'] = df['sleep_score'].shift(-1)
        
        # レポートを生成
        report = self._generate_report(df, start_date, end_date, days)
        
        return report
    
    def _generate_report(self, df: pd.DataFrame, start_date: date, end_date: date, days: int) -> str:
        """レポートを生成"""
        report = "=" * 80 + "\n"
        report += f"過去{days}日間の包括的分析レポート\n"
        report += f"分析期間: {start_date} ～ {end_date}\n"
        report += "=" * 80 + "\n\n"
        
        # 1. 日ごとの詳細データ
        report += "【1. 日ごとの詳細データ】\n"
        report += "-" * 80 + "\n"
        for _, row in df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d (%A)')
            report += f"\n{date_str}:\n"
            
            if pd.notna(row['sleep_minutes']):
                sleep_hours = row['sleep_minutes'] / 60
                report += f"  睡眠: {sleep_hours:.1f}時間"
                if pd.notna(row['deep_sleep_minutes']):
                    report += f"（深い睡眠: {row['deep_sleep_minutes']:.0f}分"
                    if pd.notna(row['rem_sleep_minutes']):
                        report += f", REM: {row['rem_sleep_minutes']:.0f}分"
                    report += "）"
                report += "\n"
            
            if pd.notna(row['recovery_score']):
                report += f"  リカバリースコア: {row['recovery_score']:.0f}pt"
                if pd.notna(row['sleep_score']):
                    report += f", 睡眠スコア: {row['sleep_score']:.0f}pt"
                if pd.notna(row['stress_score']):
                    report += f", ストレススコア: {row['stress_score']:.0f}pt"
                report += "\n"
            
            if pd.notna(row['hrv_avg']):
                report += f"  HRV: {row['hrv_avg']:.1f}ms"
                if pd.notna(row['hrv_baseline']):
                    diff = row['hrv_avg'] - row['hrv_baseline']
                    diff_pct = (diff / row['hrv_baseline'] * 100) if row['hrv_baseline'] > 0 else 0
                    report += f"（ベースライン: {row['hrv_baseline']:.1f}ms, 差: {diff:+.1f}ms ({diff_pct:+.1f}%)）"
                report += "\n"
            
            if pd.notna(row['resting_heart_rate']):
                report += f"  安静時心拍数: {row['resting_heart_rate']:.0f}bpm\n"
            
            if pd.notna(row['steps']):
                report += f"  歩数: {row['steps']:.0f}歩"
                if row.get('is_long_run', False):
                    report += " (高負荷運動日)"
                if pd.notna(row['active_energy']):
                    report += f", アクティブエネルギー: {row['active_energy']:.0f}kcal"
                report += "\n"
            
            if row.get('running_duration', 0) > 0:
                report += f"  ランニング: {row['running_duration']:.0f}分"
                if row.get('running_energy', 0) > 0:
                    report += f", {row['running_energy']:.0f}kcal"
                report += "\n"
        
        # 2. 高負荷運動の影響分析
        report += "\n" + "=" * 80 + "\n"
        report += "【2. 高負荷運動（20000歩以上）の影響分析】\n"
        report += "-" * 80 + "\n"
        
        long_run_days = df[df['is_long_run'] == True]
        normal_days = df[df['is_long_run'] == False]
        
        if len(long_run_days) > 0 and len(normal_days) > 0:
            report += f"高負荷運動日: {len(long_run_days)}日\n"
            report += f"通常日: {len(normal_days)}日\n\n"
            
            # 当日の影響
            report += "【当日の影響】\n"
            for metric, label in [
                ('sleep_minutes', '睡眠時間'),
                ('deep_sleep_minutes', '深い睡眠'),
                ('recovery_score', 'リカバリースコア'),
                ('sleep_score', '睡眠スコア'),
                ('hrv_avg', 'HRV'),
            ]:
                if metric in long_run_days.columns and metric in normal_days.columns:
                    long_run_val = long_run_days[metric].mean()
                    normal_val = normal_days[metric].mean()
                    if pd.notna(long_run_val) and pd.notna(normal_val):
                        diff = long_run_val - normal_val
                        if metric == 'sleep_minutes':
                            report += f"  {label}: 高負荷日 {long_run_val:.0f}分 vs 通常日 {normal_val:.0f}分（{diff:+.0f}分）\n"
                        elif metric == 'hrv_avg':
                            report += f"  {label}: 高負荷日 {long_run_val:.1f}ms vs 通常日 {normal_val:.1f}ms（{diff:+.1f}ms）\n"
                        else:
                            report += f"  {label}: 高負荷日 {long_run_val:.0f}pt vs 通常日 {normal_val:.0f}pt（{diff:+.0f}pt）\n"
            
            # 翌日の影響
            report += "\n【翌日の影響】\n"
            for metric, label in [
                ('next_day_sleep', '睡眠時間'),
                ('next_day_deep_sleep', '深い睡眠'),
                ('next_day_recovery', 'リカバリースコア'),
                ('next_day_sleep_score', '睡眠スコア'),
                ('next_day_hrv', 'HRV'),
            ]:
                if metric in long_run_days.columns and metric in normal_days.columns:
                    long_run_val = long_run_days[metric].mean()
                    normal_val = normal_days[metric].mean()
                    if pd.notna(long_run_val) and pd.notna(normal_val):
                        diff = long_run_val - normal_val
                        if metric == 'next_day_sleep' or metric == 'next_day_deep_sleep':
                            report += f"  {label}: 高負荷日の翌日 {long_run_val:.0f}分 vs 通常日の翌日 {normal_val:.0f}分（{diff:+.0f}分）\n"
                        elif metric == 'next_day_hrv':
                            report += f"  {label}: 高負荷日の翌日 {long_run_val:.1f}ms vs 通常日の翌日 {normal_val:.1f}ms（{diff:+.1f}ms）\n"
                        else:
                            report += f"  {label}: 高負荷日の翌日 {long_run_val:.0f}pt vs 通常日の翌日 {normal_val:.0f}pt（{diff:+.0f}pt）\n"
        
        # 3. 曜日ごとのパターン
        report += "\n" + "=" * 80 + "\n"
        report += "【3. 曜日ごとのパターン】\n"
        report += "-" * 80 + "\n"
        
        weekday_stats = df.groupby('weekday').agg({
            'recovery_score': 'mean',
            'sleep_score': 'mean',
            'sleep_minutes': 'mean',
            'deep_sleep_minutes': 'mean',
            'hrv_avg': 'mean',
            'steps': 'mean',
        })
        
        for weekday in weekday_stats.index:
            stats = weekday_stats.loc[weekday]
            report += f"\n{weekday}:\n"
            if pd.notna(stats['recovery_score']):
                report += f"  平均リカバリースコア: {stats['recovery_score']:.0f}pt\n"
            if pd.notna(stats['sleep_score']):
                report += f"  平均睡眠スコア: {stats['sleep_score']:.0f}pt\n"
            if pd.notna(stats['sleep_minutes']):
                report += f"  平均睡眠時間: {stats['sleep_minutes']/60:.1f}時間\n"
            if pd.notna(stats['deep_sleep_minutes']):
                report += f"  平均深い睡眠: {stats['deep_sleep_minutes']:.0f}分\n"
            if pd.notna(stats['hrv_avg']):
                report += f"  平均HRV: {stats['hrv_avg']:.1f}ms\n"
            if pd.notna(stats['steps']):
                report += f"  平均歩数: {stats['steps']:.0f}歩\n"
        
        # 4. 前日の活動が翌日の回復に与える影響
        report += "\n" + "=" * 80 + "\n"
        report += "【4. 前日の活動が翌日の回復に与える影響】\n"
        report += "-" * 80 + "\n"
        
        # 歩数でグループ化
        df['steps_category'] = pd.cut(
            df['prev_day_steps'],
            bins=[0, 5000, 10000, 15000, 20000, float('inf')],
            labels=['低（5000歩未満）', '中（5000-10000歩）', '高（10000-15000歩）', '非常に高（15000-20000歩）', '最高（20000歩以上）']
        )
        
        steps_recovery = df.groupby('steps_category', observed=True).agg({
            'next_day_recovery': 'mean',
            'next_day_deep_sleep': 'mean',
            'next_day_sleep_score': 'mean',
            'next_day_hrv': 'mean',
        })
        
        for category in steps_recovery.index:
            stats = steps_recovery.loc[category]
            report += f"\n前日の歩数が{category}の場合:\n"
            if pd.notna(stats['next_day_recovery']):
                report += f"  翌日のリカバリースコア: {stats['next_day_recovery']:.0f}pt\n"
            if pd.notna(stats['next_day_deep_sleep']):
                report += f"  翌日の深い睡眠: {stats['next_day_deep_sleep']:.0f}分\n"
            if pd.notna(stats['next_day_sleep_score']):
                report += f"  翌日の睡眠スコア: {stats['next_day_sleep_score']:.0f}pt\n"
            if pd.notna(stats['next_day_hrv']):
                report += f"  翌日のHRV: {stats['next_day_hrv']:.1f}ms\n"
        
        # 5. 睡眠の質とHRVの関係
        report += "\n" + "=" * 80 + "\n"
        report += "【5. 睡眠の質とHRVの関係】\n"
        report += "-" * 80 + "\n"
        
        if 'deep_sleep_minutes' in df.columns and 'hrv_avg' in df.columns:
            valid_data = df[['deep_sleep_minutes', 'hrv_avg']].dropna()
            if len(valid_data) > 2:
                corr = valid_data['deep_sleep_minutes'].corr(valid_data['hrv_avg'])
                report += f"深い睡眠の時間とHRVの相関係数: {corr:.2f}\n"
                
                if corr > 0.3:
                    report += "→ 強い正の相関があります。深い睡眠が増えるとHRVも向上する傾向があります。\n"
                elif corr < -0.3:
                    report += "→ 負の相関があります。他の要因も影響している可能性があります。\n"
                else:
                    report += "→ 弱い相関です。\n"
        
        # 6. 睡眠時間と深い睡眠のバランス
        report += "\n" + "=" * 80 + "\n"
        report += "【6. 睡眠時間と深い睡眠のバランス】\n"
        report += "-" * 80 + "\n"
        
        if 'sleep_minutes' in df.columns and 'deep_sleep_minutes' in df.columns:
            valid_data = df[['sleep_minutes', 'deep_sleep_minutes', 'recovery_score']].dropna()
            if len(valid_data) > 2:
                # 睡眠時間でグループ化
                valid_data['sleep_hour_bin'] = pd.cut(
                    valid_data['sleep_minutes'] / 60,
                    bins=[0, 6, 7, 8, 9, float('inf')],
                    labels=['6h未満', '6-7h', '7-8h', '8-9h', '9h以上']
                )
                
                sleep_recovery = valid_data.groupby('sleep_hour_bin', observed=True).agg({
                    'deep_sleep_minutes': 'mean',
                    'recovery_score': 'mean',
                })
                
                for bin_name in sleep_recovery.index:
                    stats = sleep_recovery.loc[bin_name]
                    report += f"\n睡眠時間が{bin_name}の場合:\n"
                    if pd.notna(stats['deep_sleep_minutes']):
                        report += f"  平均深い睡眠: {stats['deep_sleep_minutes']:.0f}分\n"
                    if pd.notna(stats['recovery_score']):
                        report += f"  平均リカバリースコア: {stats['recovery_score']:.0f}pt\n"
        
        # 7. 当日の歩数がその日の睡眠に与える影響
        report += "\n" + "=" * 80 + "\n"
        report += "【7. 当日の歩数がその日の睡眠に与える影響】\n"
        report += "-" * 80 + "\n"
        
        if 'steps' in df.columns and 'sleep_minutes' in df.columns:
            valid_data = df[['steps', 'sleep_minutes', 'deep_sleep_minutes', 'sleep_score', 'recovery_score']].dropna()
            if len(valid_data) > 2:
                # 歩数でグループ化
                valid_data['steps_category'] = pd.cut(
                    valid_data['steps'],
                    bins=[0, 5000, 10000, 15000, 20000, float('inf')],
                    labels=['低（5000歩未満）', '中（5000-10000歩）', '高（10000-15000歩）', '非常に高（15000-20000歩）', '最高（20000歩以上）']
                )
                
                steps_sleep = valid_data.groupby('steps_category', observed=True).agg({
                    'sleep_minutes': 'mean',
                    'deep_sleep_minutes': 'mean',
                    'sleep_score': 'mean',
                    'recovery_score': 'mean',
                })
                
                for category in steps_sleep.index:
                    stats = steps_sleep.loc[category]
                    report += f"\n当日の歩数が{category}の場合:\n"
                    if pd.notna(stats['sleep_minutes']):
                        report += f"  その日の睡眠時間: {stats['sleep_minutes']/60:.1f}時間 ({stats['sleep_minutes']:.0f}分)\n"
                    if pd.notna(stats['deep_sleep_minutes']):
                        report += f"  その日の深い睡眠: {stats['deep_sleep_minutes']:.0f}分\n"
                    if pd.notna(stats['sleep_score']):
                        report += f"  その日の睡眠スコア: {stats['sleep_score']:.0f}pt\n"
                    if pd.notna(stats['recovery_score']):
                        report += f"  その日のリカバリースコア: {stats['recovery_score']:.0f}pt\n"
                
                # 相関分析
                corr_sleep = valid_data['steps'].corr(valid_data['sleep_minutes'])
                corr_deep = valid_data['steps'].corr(valid_data['deep_sleep_minutes'])
                corr_sleep_score = valid_data['steps'].corr(valid_data['sleep_score'])
                
                report += f"\n【相関分析】\n"
                if pd.notna(corr_sleep):
                    report += f"  歩数と睡眠時間の相関係数: {corr_sleep:.2f}\n"
                if pd.notna(corr_deep):
                    report += f"  歩数と深い睡眠の相関係数: {corr_deep:.2f}\n"
                if pd.notna(corr_sleep_score):
                    report += f"  歩数と睡眠スコアの相関係数: {corr_sleep_score:.2f}\n"
        
        # 8. 追加のクロス分析
        report += "\n" + "=" * 80 + "\n"
        report += "【8. 追加のクロス分析（気づきにくい関連性）】\n"
        report += "-" * 80 + "\n"
        
        # 8.1 睡眠時間と深い睡眠のバランスがリカバリースコアに与える影響
        if 'sleep_minutes' in df.columns and 'deep_sleep_minutes' in df.columns and 'recovery_score' in df.columns:
            valid_data = df[['sleep_minutes', 'deep_sleep_minutes', 'recovery_score']].dropna()
            if len(valid_data) > 5:
                valid_data['sleep_hours'] = valid_data['sleep_minutes'] / 60
                valid_data['deep_sleep_ratio'] = valid_data['deep_sleep_minutes'] / valid_data['sleep_minutes'] * 100
                
                # 睡眠時間と深い睡眠の割合で4象限に分類
                sleep_median = valid_data['sleep_hours'].median()
                deep_ratio_median = valid_data['deep_sleep_ratio'].median()
                
                quadrant1 = valid_data[(valid_data['sleep_hours'] >= sleep_median) & (valid_data['deep_sleep_ratio'] >= deep_ratio_median)]  # 睡眠長+深い睡眠多
                quadrant2 = valid_data[(valid_data['sleep_hours'] < sleep_median) & (valid_data['deep_sleep_ratio'] >= deep_ratio_median)]  # 睡眠短+深い睡眠多
                quadrant3 = valid_data[(valid_data['sleep_hours'] >= sleep_median) & (valid_data['deep_sleep_ratio'] < deep_ratio_median)]  # 睡眠長+深い睡眠少
                quadrant4 = valid_data[(valid_data['sleep_hours'] < sleep_median) & (valid_data['deep_sleep_ratio'] < deep_ratio_median)]  # 睡眠短+深い睡眠少
                
                report += "\n【8.1 睡眠時間と深い睡眠のバランスがリカバリースコアに与える影響】\n"
                if len(quadrant1) > 0:
                    report += f"  睡眠時間長+深い睡眠多: 平均リカバリースコア {quadrant1['recovery_score'].mean():.0f}pt (n={len(quadrant1)})\n"
                if len(quadrant2) > 0:
                    report += f"  睡眠時間短+深い睡眠多: 平均リカバリースコア {quadrant2['recovery_score'].mean():.0f}pt (n={len(quadrant2)})\n"
                if len(quadrant3) > 0:
                    report += f"  睡眠時間長+深い睡眠少: 平均リカバリースコア {quadrant3['recovery_score'].mean():.0f}pt (n={len(quadrant3)})\n"
                if len(quadrant4) > 0:
                    report += f"  睡眠時間短+深い睡眠少: 平均リカバリースコア {quadrant4['recovery_score'].mean():.0f}pt (n={len(quadrant4)})\n"
        
        # 8.2 HRVと安静時心拍数の関係
        if 'hrv_avg' in df.columns and 'resting_heart_rate' in df.columns and 'recovery_score' in df.columns:
            valid_data = df[['hrv_avg', 'resting_heart_rate', 'recovery_score']].dropna()
            if len(valid_data) > 5:
                hrv_median = valid_data['hrv_avg'].median()
                hr_median = valid_data['resting_heart_rate'].median()
                
                high_hrv_low_hr = valid_data[(valid_data['hrv_avg'] >= hrv_median) & (valid_data['resting_heart_rate'] <= hr_median)]
                high_hrv_high_hr = valid_data[(valid_data['hrv_avg'] >= hrv_median) & (valid_data['resting_heart_rate'] > hr_median)]
                low_hrv_low_hr = valid_data[(valid_data['hrv_avg'] < hrv_median) & (valid_data['resting_heart_rate'] <= hr_median)]
                low_hrv_high_hr = valid_data[(valid_data['hrv_avg'] < hrv_median) & (valid_data['resting_heart_rate'] > hr_median)]
                
                report += "\n【8.2 HRVと安静時心拍数の組み合わせがリカバリースコアに与える影響】\n"
                if len(high_hrv_low_hr) > 0:
                    report += f"  HRV高+心拍数低（理想）: 平均リカバリースコア {high_hrv_low_hr['recovery_score'].mean():.0f}pt (n={len(high_hrv_low_hr)})\n"
                if len(high_hrv_high_hr) > 0:
                    report += f"  HRV高+心拍数高: 平均リカバリースコア {high_hrv_high_hr['recovery_score'].mean():.0f}pt (n={len(high_hrv_high_hr)})\n"
                if len(low_hrv_low_hr) > 0:
                    report += f"  HRV低+心拍数低: 平均リカバリースコア {low_hrv_low_hr['recovery_score'].mean():.0f}pt (n={len(low_hrv_low_hr)})\n"
                if len(low_hrv_high_hr) > 0:
                    report += f"  HRV低+心拍数高（要注意）: 平均リカバリースコア {low_hrv_high_hr['recovery_score'].mean():.0f}pt (n={len(low_hrv_high_hr)})\n"
        
        # 8.3 週末と平日のパターンの違い
        if 'weekday' in df.columns:
            df['is_weekend'] = df['weekday'].isin(['Saturday', 'Sunday'])
            weekend = df[df['is_weekend'] == True]
            weekday = df[df['is_weekend'] == False]
            
            report += "\n【8.3 週末と平日のパターンの違い】\n"
            if len(weekend) > 0 and len(weekday) > 0:
                for metric, label in [
                    ('sleep_minutes', '睡眠時間'),
                    ('deep_sleep_minutes', '深い睡眠'),
                    ('recovery_score', 'リカバリースコア'),
                    ('steps', '歩数'),
                    ('hrv_avg', 'HRV'),
                ]:
                    if metric in weekend.columns and metric in weekday.columns:
                        weekend_val = weekend[metric].mean()
                        weekday_val = weekday[metric].mean()
                        if pd.notna(weekend_val) and pd.notna(weekday_val):
                            diff = weekend_val - weekday_val
                            if metric == 'sleep_minutes':
                                report += f"  {label}: 週末 {weekend_val/60:.1f}時間 vs 平日 {weekday_val/60:.1f}時間（{diff/60:+.1f}時間）\n"
                            elif metric == 'hrv_avg':
                                report += f"  {label}: 週末 {weekend_val:.1f}ms vs 平日 {weekday_val:.1f}ms（{diff:+.1f}ms）\n"
                            elif metric == 'steps':
                                report += f"  {label}: 週末 {weekend_val:.0f}歩 vs 平日 {weekday_val:.0f}歩（{diff:+.0f}歩）\n"
                            else:
                                report += f"  {label}: 週末 {weekend_val:.0f} vs 平日 {weekday_val:.0f}（{diff:+.0f}）\n"
        
        # 8.4 ランニングの有無と睡眠の質の関係
        if 'running_duration' in df.columns:
            df['has_running'] = df['running_duration'] > 0
            running_days = df[df['has_running'] == True]
            no_running_days = df[df['has_running'] == False]
            
            report += "\n【8.4 ランニングの有無と睡眠の質の関係】\n"
            if len(running_days) > 0 and len(no_running_days) > 0:
                for metric, label in [
                    ('sleep_minutes', '睡眠時間'),
                    ('deep_sleep_minutes', '深い睡眠'),
                    ('sleep_score', '睡眠スコア'),
                    ('recovery_score', 'リカバリースコア'),
                ]:
                    if metric in running_days.columns and metric in no_running_days.columns:
                        running_val = running_days[metric].mean()
                        no_running_val = no_running_days[metric].mean()
                        if pd.notna(running_val) and pd.notna(no_running_val):
                            diff = running_val - no_running_val
                            if metric == 'sleep_minutes':
                                report += f"  {label}: ランニング日 {running_val/60:.1f}時間 vs 非ランニング日 {no_running_val/60:.1f}時間（{diff/60:+.1f}時間）\n"
                            else:
                                report += f"  {label}: ランニング日 {running_val:.0f}pt vs 非ランニング日 {no_running_val:.0f}pt（{diff:+.0f}pt）\n"
        
        # 8.5 睡眠スコアとリカバリースコアの不一致パターン
        if 'sleep_score' in df.columns and 'recovery_score' in df.columns:
            valid_data = df[['sleep_score', 'recovery_score']].dropna()
            if len(valid_data) > 5:
                valid_data['score_diff'] = valid_data['recovery_score'] - valid_data['sleep_score']
                
                # 睡眠スコアが高いのにリカバリースコアが低い日
                high_sleep_low_recovery = valid_data[(valid_data['sleep_score'] >= 70) & (valid_data['recovery_score'] < 50)]
                # 睡眠スコアが低いのにリカバリースコアが高い日
                low_sleep_high_recovery = valid_data[(valid_data['sleep_score'] < 50) & (valid_data['recovery_score'] >= 70)]
                
                report += "\n【8.5 睡眠スコアとリカバリースコアの不一致パターン】\n"
                if len(high_sleep_low_recovery) > 0:
                    report += f"  睡眠スコア高+リカバリースコア低（睡眠は良いが回復していない）: {len(high_sleep_low_recovery)}日\n"
                    report += f"    平均睡眠スコア: {high_sleep_low_recovery['sleep_score'].mean():.0f}pt, 平均リカバリースコア: {high_sleep_low_recovery['recovery_score'].mean():.0f}pt\n"
                if len(low_sleep_high_recovery) > 0:
                    report += f"  睡眠スコア低+リカバリースコア高（睡眠は悪いが回復している）: {len(low_sleep_high_recovery)}日\n"
                    report += f"    平均睡眠スコア: {low_sleep_high_recovery['sleep_score'].mean():.0f}pt, 平均リカバリースコア: {low_sleep_high_recovery['recovery_score'].mean():.0f}pt\n"
        
        # 8.6 アクティブエネルギーと歩数の効率性
        if 'active_energy' in df.columns and 'steps' in df.columns:
            valid_data = df[['active_energy', 'steps']].dropna()
            if len(valid_data) > 5:
                valid_data['energy_per_step'] = valid_data['active_energy'] / valid_data['steps']
                
                # エネルギー効率が高い日（1歩あたりのエネルギーが高い）
                high_efficiency = valid_data[valid_data['energy_per_step'] >= valid_data['energy_per_step'].quantile(0.75)]
                low_efficiency = valid_data[valid_data['energy_per_step'] <= valid_data['energy_per_step'].quantile(0.25)]
                
                report += "\n【8.6 アクティブエネルギーと歩数の効率性】\n"
                report += f"  1歩あたりの平均エネルギー: {valid_data['energy_per_step'].mean():.2f}kcal/歩\n"
                if len(high_efficiency) > 0 and len(low_efficiency) > 0:
                    report += f"  高効率日（上位25%）: 平均 {high_efficiency['energy_per_step'].mean():.2f}kcal/歩 (n={len(high_efficiency)})\n"
                    report += f"  低効率日（下位25%）: 平均 {low_efficiency['energy_per_step'].mean():.2f}kcal/歩 (n={len(low_efficiency)})\n"
                    report += f"  → 高効率日は低効率日の {high_efficiency['energy_per_step'].mean() / low_efficiency['energy_per_step'].mean():.1f}倍のエネルギーを消費\n"
        
        # 8.7 連続する高負荷運動日の影響
        if 'is_long_run' in df.columns:
            df_sorted = df.sort_values('date')
            consecutive_patterns = []
            current_streak = 0
            streak_start = None
            
            for _, row in df_sorted.iterrows():
                if row.get('is_long_run', False):
                    if current_streak == 0:
                        streak_start = row['date']
                    current_streak += 1
                else:
                    if current_streak > 1:
                        consecutive_patterns.append({
                            'start': streak_start,
                            'length': current_streak,
                        })
                    current_streak = 0
            
            if current_streak > 1:
                consecutive_patterns.append({
                    'start': streak_start,
                    'length': current_streak,
                })
            
            report += "\n【8.7 連続する高負荷運動日の影響】\n"
            if consecutive_patterns:
                report += f"  連続する高負荷運動日: {len(consecutive_patterns)}回\n"
                for pattern in consecutive_patterns:
                    report += f"    {pattern['start'].strftime('%Y-%m-%d')}から{pattern['length']}日連続\n"
            else:
                report += "  連続する高負荷運動日はありませんでした。\n"
        
        # 8.8 前日の睡眠が当日の活動に与える影響（逆方向）
        if 'prev_day_sleep' in df.columns and 'steps' in df.columns:
            valid_data = df[['prev_day_sleep', 'steps', 'active_energy']].dropna()
            if len(valid_data) > 5:
                # 前日の睡眠時間でグループ化
                valid_data['prev_sleep_category'] = pd.cut(
                    valid_data['prev_day_sleep'] / 60,
                    bins=[0, 6, 7, 8, float('inf')],
                    labels=['6h未満', '6-7h', '7-8h', '8h以上']
                )
                
                sleep_activity = valid_data.groupby('prev_sleep_category', observed=True).agg({
                    'steps': 'mean',
                    'active_energy': 'mean',
                })
                
                report += "\n【8.8 前日の睡眠が当日の活動に与える影響】\n"
                for category in sleep_activity.index:
                    stats = sleep_activity.loc[category]
                    report += f"  前日の睡眠が{category}の場合:\n"
                    if pd.notna(stats['steps']):
                        report += f"    当日の平均歩数: {stats['steps']:.0f}歩\n"
                    if pd.notna(stats['active_energy']):
                        report += f"    当日の平均アクティブエネルギー: {stats['active_energy']:.0f}kcal\n"
        
        # 8.9 深い睡眠の絶対時間と割合の最適な組み合わせ
        if 'deep_sleep_minutes' in df.columns and 'sleep_minutes' in df.columns and 'recovery_score' in df.columns:
            valid_data = df[['deep_sleep_minutes', 'sleep_minutes', 'recovery_score']].dropna()
            if len(valid_data) > 5:
                valid_data['deep_ratio'] = valid_data['deep_sleep_minutes'] / valid_data['sleep_minutes'] * 100
                
                # 深い睡眠が60分以上かつ割合が15%以上の日
                optimal_deep = valid_data[(valid_data['deep_sleep_minutes'] >= 60) & (valid_data['deep_ratio'] >= 15)]
                # 深い睡眠が60分未満または割合が15%未満の日
                suboptimal_deep = valid_data[(valid_data['deep_sleep_minutes'] < 60) | (valid_data['deep_ratio'] < 15)]
                
                report += "\n【8.9 深い睡眠の絶対時間と割合の最適な組み合わせ】\n"
                if len(optimal_deep) > 0 and len(suboptimal_deep) > 0:
                    report += f"  最適な深い睡眠（60分以上かつ15%以上）: {len(optimal_deep)}日\n"
                    report += f"    平均リカバリースコア: {optimal_deep['recovery_score'].mean():.0f}pt\n"
                    report += f"  最適でない深い睡眠: {len(suboptimal_deep)}日\n"
                    report += f"    平均リカバリースコア: {suboptimal_deep['recovery_score'].mean():.0f}pt\n"
                    diff = optimal_deep['recovery_score'].mean() - suboptimal_deep['recovery_score'].mean()
                    report += f"  → 最適な深い睡眠の日のリカバリースコアが{diff:.0f}pt{'高い' if diff > 0 else '低い'}\n"
        
        # 8.10 曜日と高負荷運動の組み合わせ
        if 'weekday' in df.columns and 'is_long_run' in df.columns:
            weekday_long_run = df.groupby(['weekday', 'is_long_run']).size().unstack(fill_value=0)
            
            report += "\n【8.10 曜日と高負荷運動の組み合わせ】\n"
            if not weekday_long_run.empty:
                for weekday in weekday_long_run.index:
                    long_run_count = weekday_long_run.loc[weekday, True] if True in weekday_long_run.columns else 0
                    normal_count = weekday_long_run.loc[weekday, False] if False in weekday_long_run.columns else 0
                    total = long_run_count + normal_count
                    if total > 0:
                        long_run_pct = (long_run_count / total * 100) if total > 0 else 0
                        report += f"  {weekday}: 高負荷運動日 {long_run_count}日 / 通常日 {normal_count}日 ({long_run_pct:.0f}%が高負荷運動日)\n"
        
        # 9. 気づきにくい関連性
        report += "\n" + "=" * 80 + "\n"
        report += "【9. 気づきにくい関連性と示唆】\n"
        report += "-" * 80 + "\n"
        
        insights = []
        
        # 7.1 前日の睡眠が翌日の活動に与える影響
        if 'prev_day_sleep' in df.columns and 'steps' in df.columns:
            valid_data = df[['prev_day_sleep', 'steps']].dropna()
            if len(valid_data) > 2:
                corr = valid_data['prev_day_sleep'].corr(valid_data['steps'])
                if abs(corr) > 0.3:
                    insights.append(f"前日の睡眠時間と当日の歩数には{'正' if corr > 0 else '負'}の相関（{corr:.2f}）があります。")
        
        # 7.2 深い睡眠の絶対時間とリカバリースコアの関係
        if 'deep_sleep_minutes' in df.columns and 'recovery_score' in df.columns:
            valid_data = df[['deep_sleep_minutes', 'recovery_score']].dropna()
            if len(valid_data) > 2:
                # 深い睡眠が60分以上の日と未満の日を比較
                high_deep = valid_data[valid_data['deep_sleep_minutes'] >= 60]
                low_deep = valid_data[valid_data['deep_sleep_minutes'] < 60]
                if len(high_deep) > 0 and len(low_deep) > 0:
                    high_recovery = high_deep['recovery_score'].mean()
                    low_recovery = low_deep['recovery_score'].mean()
                    if pd.notna(high_recovery) and pd.notna(low_recovery):
                        diff = high_recovery - low_recovery
                        insights.append(f"深い睡眠が60分以上の日のリカバリースコアは、60分未満の日より平均{diff:.0f}pt{'高い' if diff > 0 else '低い'}です。")
        
        # 7.3 HRVとベースラインの関係
        if 'hrv_avg' in df.columns and 'hrv_baseline' in df.columns:
            valid_data = df[['hrv_avg', 'hrv_baseline', 'recovery_score']].dropna()
            if len(valid_data) > 0:
                valid_data['hrv_ratio'] = valid_data['hrv_avg'] / valid_data['hrv_baseline']
                high_hrv = valid_data[valid_data['hrv_ratio'] >= 1.0]
                low_hrv = valid_data[valid_data['hrv_ratio'] < 1.0]
                if len(high_hrv) > 0 and len(low_hrv) > 0:
                    high_recovery = high_hrv['recovery_score'].mean()
                    low_recovery = low_hrv['recovery_score'].mean()
                    if pd.notna(high_recovery) and pd.notna(low_recovery):
                        diff = high_recovery - low_recovery
                        insights.append(f"HRVがベースライン以上の日のリカバリースコアは、ベースライン未満の日より平均{diff:.0f}pt{'高い' if diff > 0 else '低い'}です。")
        
        # 7.4 アクティブエネルギーと翌日の睡眠の関係
        if 'active_energy' in df.columns and 'next_day_sleep' in df.columns:
            valid_data = df[['active_energy', 'next_day_sleep']].dropna()
            if len(valid_data) > 2:
                corr = valid_data['active_energy'].corr(valid_data['next_day_sleep'])
                if abs(corr) > 0.3:
                    insights.append(f"アクティブエネルギーと翌日の睡眠時間には{'正' if corr > 0 else '負'}の相関（{corr:.2f}）があります。")
        
        # 7.5 ストレススコアと睡眠スコアの関係
        if 'stress_score' in df.columns and 'sleep_score' in df.columns:
            valid_data = df[['stress_score', 'sleep_score']].dropna()
            if len(valid_data) > 2:
                corr = valid_data['stress_score'].corr(valid_data['sleep_score'])
                if abs(corr) > 0.3:
                    insights.append(f"ストレススコアと睡眠スコアには{'正' if corr > 0 else '負'}の相関（{corr:.2f}）があります。")
        
        # 7.6 連続する高負荷運動日の影響
        if 'is_long_run' in df.columns:
            consecutive_long_runs = []
            current_streak = 0
            for _, row in df.iterrows():
                if row.get('is_long_run', False):
                    current_streak += 1
                else:
                    if current_streak > 1:
                        consecutive_long_runs.append(current_streak)
                    current_streak = 0
            if consecutive_long_runs:
                insights.append(f"連続する高負荷運動日が{max(consecutive_long_runs)}日続いたことがあります。")
        
        # 7.7 最適な睡眠時間の特定
        if 'sleep_minutes' in df.columns and 'recovery_score' in df.columns:
            valid_data = df[['sleep_minutes', 'recovery_score']].dropna()
            if len(valid_data) > 2:
                valid_data['sleep_hours'] = valid_data['sleep_minutes'] / 60
                # リカバリースコアが高い日の睡眠時間
                high_recovery = valid_data[valid_data['recovery_score'] >= valid_data['recovery_score'].quantile(0.75)]
                if len(high_recovery) > 0:
                    optimal_sleep = high_recovery['sleep_hours'].mean()
                    insights.append(f"リカバリースコアが高い日の平均睡眠時間は{optimal_sleep:.1f}時間です。")
        
        # インサイトを出力
        if insights:
            for i, insight in enumerate(insights, 1):
                report += f"{i}. {insight}\n"
        else:
            report += "データが不足しているため、追加のインサイトを生成できませんでした。\n"
        
        # 10. 推奨事項
        report += "\n" + "=" * 80 + "\n"
        report += "【10. 推奨事項】\n"
        report += "-" * 80 + "\n"
        
        recommendations = []
        
        # 平均睡眠時間が7時間未満の場合
        if 'sleep_minutes' in df.columns:
            avg_sleep = df['sleep_minutes'].mean()
            if pd.notna(avg_sleep) and avg_sleep < 420:  # 7時間未満
                recommendations.append(f"平均睡眠時間が{avg_sleep/60:.1f}時間と短めです。7-8時間の睡眠を目標にしましょう。")
        
        # 平均深い睡眠が30分未満の場合
        if 'deep_sleep_minutes' in df.columns:
            avg_deep = df['deep_sleep_minutes'].mean()
            if pd.notna(avg_deep) and avg_deep < 30:
                recommendations.append(f"平均深い睡眠が{avg_deep:.0f}分と少なめです。睡眠の質を改善する対策を検討してください。")
        
        # HRVがベースラインより低い日が多い場合
        if 'hrv_avg' in df.columns and 'hrv_baseline' in df.columns:
            valid_data = df[['hrv_avg', 'hrv_baseline']].dropna()
            if len(valid_data) > 0:
                valid_data['hrv_ratio'] = valid_data['hrv_avg'] / valid_data['hrv_baseline']
                low_hrv_days = len(valid_data[valid_data['hrv_ratio'] < 0.9])
                if low_hrv_days > len(valid_data) * 0.5:
                    recommendations.append(f"HRVがベースラインより10%以上低い日が{low_hrv_days}日ありました。休息を優先することをお勧めします。")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"
        else:
            report += "特に問題は見つかりませんでした。現在の生活パターンを維持しましょう。\n"
        
        report += "\n" + "=" * 80 + "\n"
        report += f"レポート生成日時: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 80 + "\n"
        
        return report

