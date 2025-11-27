#!/usr/bin/env python3
"""
データベースからデータを読み込んで、インサイトを生成するスクリプト
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_setup import Database
from src.insights.phase1_insights import Phase1Insights


def main():
    """メイン処理"""
    import sys
    from datetime import datetime, timedelta
    
    # コマンドライン引数で期間を指定可能
    months = 3
    if len(sys.argv) > 1:
        try:
            months = int(sys.argv[1])
        except ValueError:
            print(f"警告: 無効な引数 '{sys.argv[1]}'。デフォルトの3ヶ月を使用します。")
    
    print("=" * 60)
    print(f"インサイト生成開始（最近{months}ヶ月）")
    print("=" * 60)
    
    # データベースからデータを読み込み
    db = Database()
    
    # 最近Nヶ月のデータのみを取得
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=months * 30)
    
    daily_health_list = db.get_all_daily_health(start_date=start_date, end_date=end_date)
    
    if not daily_health_list:
        print("エラー: データベースにデータがありません")
        print("先に import_to_db.py を実行してください")
        return
    
    # DataFrameに変換
    import pandas as pd
    from src.models.health_data import DailyHealth
    
    data = []
    for daily_health in daily_health_list:
        data.append({
            'date': daily_health.date,
            'sleep_minutes': daily_health.sleep_minutes,
            'deep_sleep_minutes': daily_health.deep_sleep_minutes,
            'rem_sleep_minutes': daily_health.rem_sleep_minutes,
            'light_sleep_minutes': daily_health.light_sleep_minutes,
            'hrv_avg': daily_health.hrv_avg,
            'hrv_deep_sleep_avg': daily_health.hrv_deep_sleep_avg,
            'hrv_deep_sleep_stddev': daily_health.hrv_deep_sleep_stddev,
            'hrv_min': daily_health.hrv_min,
            'hrv_max': daily_health.hrv_max,
            'hrv_baseline': daily_health.hrv_baseline,
            'resting_heart_rate': daily_health.resting_heart_rate,
            'avg_heart_rate': daily_health.avg_heart_rate,
            'steps': daily_health.steps,
            'active_energy': daily_health.active_energy,
            'recovery_score': daily_health.recovery_score,
            'stress_score': daily_health.stress_score,
        })
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    
    if df.empty:
        print("エラー: 指定期間にデータがありません")
        return
    
    print(f"データ件数: {len(df)}日")
    print(f"データ期間: {df['date'].min()} ～ {df['date'].max()}")
    
    # インサイトを生成
    insights_gen = Phase1Insights(df)
    report = insights_gen.format_weekly_report()
    
    print("\n" + "=" * 60)
    print("生成されたインサイト")
    print("=" * 60)
    print("\n" + report)
    
    # レポートをファイルに保存
    output_file = project_root / 'data' / 'processed' / 'weekly_insights.txt'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nレポートを保存しました: {output_file}")
    print("\n処理完了！")


if __name__ == '__main__':
    main()

