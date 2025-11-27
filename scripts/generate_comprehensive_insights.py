"""
包括的なインサイトを生成するスクリプト
"""
import sys
from pathlib import Path
from datetime import date

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.db_setup import Database
from src.insights.comprehensive_insights import ComprehensiveInsights


def main():
    """メイン処理"""
    # コマンドライン引数から日数を取得（デフォルト: 7日）
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print(f"警告: 無効な日数 '{sys.argv[1]}'。デフォルトの7日を使用します。")
    
    print("=" * 80)
    print(f"包括的なインサイト生成開始（過去{days}日間）")
    print("=" * 80)
    
    # データベースを初期化
    db = Database()
    
    # インサイト生成器を初期化
    insights = ComprehensiveInsights(db)
    
    # 今日の日付
    today = date.today()
    
    # 包括的な分析を実行
    report = insights.analyze_comprehensive(today, days)
    
    print("\n" + report)
    
    # ファイルに保存
    output_path = Path('data/processed/comprehensive_insights.txt')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nレポートを保存しました: {output_path}")
    print("\n処理完了！")


if __name__ == '__main__':
    main()

