#!/usr/bin/env python3
"""
処理済みデータをデータベースにインポートし、スコアを計算するスクリプト
"""
import sys
from pathlib import Path
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_setup import Database
from src.calculators.recovery_stress import RecoveryStressCalculator
from src.calculators.sleep_score import SleepScoreCalculator
from src.models.health_data import DailyHealth
from datetime import date


def main():
    """メイン処理"""
    print("=" * 60)
    print("データベースへのインポート開始")
    print("=" * 60)
    
    # データベースを初期化
    db = Database()
    print("データベースを初期化しました")
    
    # CSVファイルを読み込み
    csv_path = project_root / 'data' / 'processed' / 'daily_health.csv'
    
    if not csv_path.exists():
        print(f"エラー: CSVファイルが見つかりません: {csv_path}")
        print("先に parse_apple_health.py を実行してください")
        return
    
    print(f"\nCSVファイルを読み込み中: {csv_path}")
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date']).dt.date
    
    print(f"データ件数: {len(df)}日")
    
    # DailyHealthオブジェクトのリストを作成
    daily_health_list = []
    for _, row in df.iterrows():
        daily_health = DailyHealth(
            date=row['date'],
            sleep_minutes=row.get('sleep_minutes') if pd.notna(row.get('sleep_minutes')) else None,
            deep_sleep_minutes=row.get('deep_sleep_minutes') if pd.notna(row.get('deep_sleep_minutes')) else None,
            rem_sleep_minutes=row.get('rem_sleep_minutes') if pd.notna(row.get('rem_sleep_minutes')) else None,
            light_sleep_minutes=row.get('light_sleep_minutes') if pd.notna(row.get('light_sleep_minutes')) else None,
            hrv_avg=row.get('hrv_avg') if pd.notna(row.get('hrv_avg')) else None,
            hrv_deep_sleep_avg=row.get('hrv_deep_sleep_avg') if pd.notna(row.get('hrv_deep_sleep_avg')) else None,
            hrv_deep_sleep_stddev=row.get('hrv_deep_sleep_stddev') if pd.notna(row.get('hrv_deep_sleep_stddev')) else None,
            hrv_min=row.get('hrv_min') if pd.notna(row.get('hrv_min')) else None,
            hrv_max=row.get('hrv_max') if pd.notna(row.get('hrv_max')) else None,
            resting_heart_rate=row.get('resting_heart_rate') if pd.notna(row.get('resting_heart_rate')) else None,
            avg_heart_rate=row.get('avg_heart_rate') if pd.notna(row.get('avg_heart_rate')) else None,
            steps=row.get('steps') if pd.notna(row.get('steps')) else None,
            active_energy=row.get('active_energy') if pd.notna(row.get('active_energy')) else None,
        )
        daily_health_list.append(daily_health)
    
    # スコア計算器を初期化（ベースライン計算用に全データを渡す）
    recovery_calculator = RecoveryStressCalculator(baseline_data=daily_health_list)
    sleep_calculator = SleepScoreCalculator()
    
    # 各日のスコアを計算してデータベースに保存
    print("\nスコアを計算中...")
    saved_count = 0
    
    for daily_health in daily_health_list:
        # リカバリースコアとストレススコアを計算
        daily_health = recovery_calculator.calculate_scores(daily_health)
        
        # 睡眠スコアを計算
        sleep_score = sleep_calculator.calculate_sleep_score(daily_health)
        daily_health.sleep_score = sleep_score
        
        # データベースに保存
        db.insert_daily_health(daily_health)
        saved_count += 1
        
        if saved_count % 10 == 0:
            print(f"  処理済み: {saved_count}日")
    
    print(f"\nデータベースへの保存完了: {saved_count}日")
    
    # データの概要を表示
    print("\n" + "=" * 60)
    print("保存されたデータの概要")
    print("=" * 60)
    
    df_db = db.to_dataframe()
    
    if not df_db.empty:
        print(f"\nデータ期間: {df_db['date'].min()} ～ {df_db['date'].max()}")
        print(f"データ件数: {len(df_db)}日")
        
        if df_db['recovery_score'].notna().any():
            print(f"\nリカバリースコア:")
            print(f"  平均: {df_db['recovery_score'].mean():.1f}pt")
            print(f"  範囲: {df_db['recovery_score'].min():.0f} ～ {df_db['recovery_score'].max():.0f}pt")
        
        if df_db['stress_score'].notna().any():
            print(f"\nストレススコア:")
            print(f"  平均: {df_db['stress_score'].mean():.1f}pt")
            print(f"  範囲: {df_db['stress_score'].min():.0f} ～ {df_db['stress_score'].max():.0f}pt")
    
    print("\n処理完了！")


if __name__ == '__main__':
    main()

