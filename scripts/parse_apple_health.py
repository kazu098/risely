#!/usr/bin/env python3
"""
Apple Health XMLデータをパースして、日次データを集計するスクリプト
"""
import sys
import os
from pathlib import Path
from datetime import date, datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.parsers.apple_health import AppleHealthParser
from src.aggregators.daily_aggregator import DailyAggregator
import pandas as pd


def main():
    """メイン処理"""
    # XMLファイルのパス
    xml_path = project_root / 'apple_health_export' / 'export.xml'
    
    if not xml_path.exists():
        print(f"エラー: XMLファイルが見つかりません: {xml_path}")
        return
    
    print("=" * 60)
    print("Apple Health XMLデータのパース開始")
    print("=" * 60)
    
    # パーサーを初期化
    parser = AppleHealthParser(str(xml_path))
    parser.parse()
    
    # データを抽出
    print("\nデータを抽出中...")
    dataframes = parser.to_dataframes()
    
    # データの概要を表示
    print("\n" + "=" * 60)
    print("抽出されたデータの概要")
    print("=" * 60)
    for data_type, df in dataframes.items():
        if not df.empty:
            print(f"\n{data_type}:")
            print(f"  レコード数: {len(df)}")
            if 'start_date' in df.columns:
                print(f"  期間: {df['start_date'].min()} ～ {df['start_date'].max()}")
    
    # 日次データを集計
    print("\n" + "=" * 60)
    print("日次データを集計中...")
    print("=" * 60)
    
    aggregator = DailyAggregator(dataframes)
    
    # データの期間を取得
    all_dates = []
    for df in dataframes.values():
        if not df.empty and 'start_date' in df.columns:
            all_dates.extend(df['start_date'].dt.date.tolist())
    
    if not all_dates:
        print("エラー: 日付データが見つかりません")
        return
    
    start_date = min(all_dates)
    end_date = max(all_dates)
    
    print(f"集計期間: {start_date} ～ {end_date}")
    
    # 日次データを集計
    daily_health_list = aggregator.aggregate_date_range(start_date, end_date)
    
    # DataFrameに変換
    daily_data = []
    for daily_health in daily_health_list:
        daily_data.append({
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
            'resting_heart_rate': daily_health.resting_heart_rate,
            'avg_heart_rate': daily_health.avg_heart_rate,
            'steps': daily_health.steps,
            'active_energy': daily_health.active_energy,
        })
    
    df_daily = pd.DataFrame(daily_data)
    
    # データを保存
    output_dir = project_root / 'data' / 'processed'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'daily_health.csv'
    df_daily.to_csv(output_file, index=False)
    
    print(f"\n日次データを保存しました: {output_file}")
    print(f"データ件数: {len(df_daily)}日")
    
    # データの概要を表示
    print("\n" + "=" * 60)
    print("集計結果の概要")
    print("=" * 60)
    print(f"\n睡眠データがある日: {df_daily['sleep_minutes'].notna().sum()}日")
    print(f"HRVデータがある日: {df_daily['hrv_avg'].notna().sum()}日")
    print(f"歩数データがある日: {df_daily['steps'].notna().sum()}日")
    
    if df_daily['sleep_minutes'].notna().any():
        print(f"\n平均睡眠時間: {df_daily['sleep_minutes'].mean():.1f}分")
        print(f"平均深い睡眠: {df_daily['deep_sleep_minutes'].mean():.1f}分")
    
    if df_daily['hrv_avg'].notna().any():
        print(f"\n平均HRV: {df_daily['hrv_avg'].mean():.2f}ms")
        print(f"HRV範囲: {df_daily['hrv_avg'].min():.2f} ～ {df_daily['hrv_avg'].max():.2f}ms")
    
    print("\n処理完了！")


if __name__ == '__main__':
    main()

