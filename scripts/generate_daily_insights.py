"""
1日単位のインサイトを生成するスクリプト
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.db_setup import Database
from src.insights.daily_insights import DailyInsights


def main():
    """メイン処理"""
    # コマンドライン引数から日数を取得（デフォルト: 7日）
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"警告: 無効な日数 '{sys.argv[1]}'。デフォルトの7日を使用します。")
    
    print("=" * 60)
    print(f"1日単位のインサイト生成開始（過去{days}日間）")
    print("=" * 60)
    
    # データベースを初期化
    db = Database()
    
    # インサイト生成器を初期化
    insights = DailyInsights(db)
    
    # 今日の日付
    today = date.today()
    
    # 日ごとの総括を生成
    report = insights.generate_daily_summary(today, days)
    
    print("\n" + report)
    
    # ファイルに保存
    output_path = Path('data/processed/daily_insights.txt')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nレポートを保存しました: {output_path}")
    print("\n処理完了！")


if __name__ == '__main__':
    main()

