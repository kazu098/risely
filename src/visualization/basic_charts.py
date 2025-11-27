"""
基本的な可視化
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from typing import Optional


# 日本語フォントの設定（macOSの場合）
plt.rcParams['font.family'] = 'Hiragino Sans'  # macOS
# Windowsの場合: 'MS Gothic'
# Linuxの場合: 'Noto Sans CJK JP'

sns.set_style("whitegrid")
sns.set_palette("husl")


class BasicCharts:
    """基本的なチャートを作成するクラス"""
    
    def __init__(self, df: pd.DataFrame):
        """
        チャート生成器を初期化
        
        パラメータ:
        - df: 日次健康データのDataFrame
        """
        self.df = df.copy()
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
            self.df = self.df.sort_values('date')
    
    def plot_sleep_trend(self, output_path: Optional[Path] = None):
        """
        睡眠時間の推移をプロット
        
        パラメータ:
        - output_path: 出力ファイルのパス（オプション）
        """
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # 総睡眠時間
        axes[0].plot(self.df['date'], self.df['sleep_minutes'] / 60, 
                    marker='o', markersize=3, linewidth=1.5)
        axes[0].set_title('総睡眠時間の推移', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('睡眠時間（時間）')
        axes[0].grid(True, alpha=0.3)
        axes[0].axhline(y=7, color='r', linestyle='--', alpha=0.5, label='推奨: 7時間')
        axes[0].axhline(y=8, color='g', linestyle='--', alpha=0.5, label='推奨: 8時間')
        axes[0].legend()
        
        # 深い睡眠の割合
        if 'deep_sleep_minutes' in self.df.columns and 'sleep_minutes' in self.df.columns:
            deep_ratio = (self.df['deep_sleep_minutes'] / self.df['sleep_minutes'] * 100)
            axes[1].plot(self.df['date'], deep_ratio, 
                        marker='o', markersize=3, linewidth=1.5, color='green')
            axes[1].set_title('深い睡眠の割合の推移', fontsize=14, fontweight='bold')
            axes[1].set_ylabel('深い睡眠の割合（%）')
            axes[1].set_xlabel('日付')
            axes[1].grid(True, alpha=0.3)
            axes[1].axhline(y=20, color='r', linestyle='--', alpha=0.5, label='推奨: 20%以上')
            axes[1].legend()
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"グラフを保存しました: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_hrv_trend(self, output_path: Optional[Path] = None):
        """
        HRVの推移をプロット
        
        パラメータ:
        - output_path: 出力ファイルのパス（オプション）
        """
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # 夜間平均HRV
        if 'hrv_avg' in self.df.columns:
            axes[0].plot(self.df['date'], self.df['hrv_avg'], 
                        marker='o', markersize=3, linewidth=1.5, color='blue')
            if 'hrv_baseline' in self.df.columns and self.df['hrv_baseline'].notna().any():
                baseline = self.df['hrv_baseline'].iloc[0]
                axes[0].axhline(y=baseline, color='r', linestyle='--', alpha=0.5, 
                               label=f'ベースライン: {baseline:.1f}ms')
            axes[0].set_title('HRV（夜間平均）の推移', fontsize=14, fontweight='bold')
            axes[0].set_ylabel('HRV（ms）')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
        
        # 深い睡眠中のHRV
        if 'hrv_deep_sleep_avg' in self.df.columns:
            axes[1].plot(self.df['date'], self.df['hrv_deep_sleep_avg'], 
                        marker='o', markersize=3, linewidth=1.5, color='green')
            axes[1].set_title('深い睡眠中のHRVの推移', fontsize=14, fontweight='bold')
            axes[1].set_ylabel('HRV（ms）')
            axes[1].set_xlabel('日付')
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"グラフを保存しました: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_recovery_stress_scores(self, output_path: Optional[Path] = None):
        """
        リカバリースコアとストレススコアの推移をプロット
        
        パラメータ:
        - output_path: 出力ファイルのパス（オプション）
        """
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # リカバリースコア
        if 'recovery_score' in self.df.columns:
            axes[0].plot(self.df['date'], self.df['recovery_score'], 
                        marker='o', markersize=3, linewidth=1.5, color='green')
            axes[0].fill_between(self.df['date'], 0, self.df['recovery_score'], 
                                alpha=0.3, color='green')
            axes[0].axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='基準: 50pt')
            axes[0].set_title('リカバリースコアの推移', fontsize=14, fontweight='bold')
            axes[0].set_ylabel('リカバリースコア（0-100）')
            axes[0].set_ylim(0, 100)
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
        
        # ストレススコア
        if 'stress_score' in self.df.columns:
            axes[1].plot(self.df['date'], self.df['stress_score'], 
                        marker='o', markersize=3, linewidth=1.5, color='red')
            axes[1].fill_between(self.df['date'], 0, self.df['stress_score'], 
                               alpha=0.3, color='red')
            axes[1].axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='基準: 50pt')
            axes[1].set_title('ストレススコアの推移', fontsize=14, fontweight='bold')
            axes[1].set_ylabel('ストレススコア（0-100、低いほどストレス低）')
            axes[1].set_ylim(0, 100)
            axes[1].grid(True, alpha=0.3)
            axes[1].legend()
        
        # 睡眠スコア
        if 'sleep_score' in self.df.columns:
            axes[2].plot(self.df['date'], self.df['sleep_score'], 
                        marker='o', markersize=3, linewidth=1.5, color='blue')
            axes[2].fill_between(self.df['date'], 0, self.df['sleep_score'], 
                               alpha=0.3, color='blue')
            axes[2].axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='基準: 50pt')
            axes[2].set_title('睡眠スコアの推移', fontsize=14, fontweight='bold')
            axes[2].set_ylabel('睡眠スコア（0-100）')
            axes[2].set_xlabel('日付')
            axes[2].set_ylim(0, 100)
            axes[2].grid(True, alpha=0.3)
            axes[2].legend()
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"グラフを保存しました: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_sleep_score_detail(self, output_path: Optional[Path] = None):
        """
        睡眠スコアの詳細（深い睡眠の時間）をプロット
        
        パラメータ:
        - output_path: 出力ファイルのパス（オプション）
        """
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # 睡眠スコア
        if 'sleep_score' in self.df.columns:
            axes[0].plot(self.df['date'], self.df['sleep_score'], 
                        marker='o', markersize=3, linewidth=1.5, color='blue')
            axes[0].fill_between(self.df['date'], 0, self.df['sleep_score'], 
                               alpha=0.3, color='blue')
            axes[0].axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='基準: 50pt')
            axes[0].set_title('睡眠スコアの推移', fontsize=14, fontweight='bold')
            axes[0].set_ylabel('睡眠スコア（0-100）')
            axes[0].set_ylim(0, 100)
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
        
        # 深い睡眠の時間（絶対時間）
        if 'deep_sleep_minutes' in self.df.columns:
            axes[1].plot(self.df['date'], self.df['deep_sleep_minutes'], 
                        marker='o', markersize=3, linewidth=1.5, color='green')
            axes[1].axhline(y=90, color='g', linestyle='--', alpha=0.5, label='推奨: 90分以上')
            axes[1].axhline(y=60, color='orange', linestyle='--', alpha=0.5, label='目標: 60分以上')
            axes[1].axhline(y=30, color='r', linestyle='--', alpha=0.5, label='最低: 30分')
            axes[1].set_title('深い睡眠の時間（絶対時間）の推移', fontsize=14, fontweight='bold')
            axes[1].set_ylabel('深い睡眠（分）')
            axes[1].set_xlabel('日付')
            axes[1].grid(True, alpha=0.3)
            axes[1].legend()
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"グラフを保存しました: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_activity_trend(self, output_path: Optional[Path] = None):
        """
        活動量の推移をプロット
        
        パラメータ:
        - output_path: 出力ファイルのパス（オプション）
        """
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # 歩数
        if 'steps' in self.df.columns:
            axes[0].plot(self.df['date'], self.df['steps'], 
                        marker='o', markersize=3, linewidth=1.5, color='blue')
            axes[0].axhline(y=8000, color='g', linestyle='--', alpha=0.5, label='推奨: 8000歩')
            axes[0].set_title('歩数の推移', fontsize=14, fontweight='bold')
            axes[0].set_ylabel('歩数')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()
        
        # アクティブエネルギー
        if 'active_energy' in self.df.columns:
            axes[1].plot(self.df['date'], self.df['active_energy'], 
                        marker='o', markersize=3, linewidth=1.5, color='orange')
            axes[1].set_title('アクティブエネルギーの推移', fontsize=14, fontweight='bold')
            axes[1].set_ylabel('アクティブエネルギー（kcal）')
            axes[1].set_xlabel('日付')
            axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"グラフを保存しました: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_correlation(self, output_path: Optional[Path] = None):
        """
        相関関係を可視化
        
        パラメータ:
        - output_path: 出力ファイルのパス（オプション）
        """
        # 相関を計算する列を選択
        corr_columns = ['sleep_minutes', 'deep_sleep_minutes', 'hrv_avg', 
                       'hrv_deep_sleep_avg', 'resting_heart_rate', 
                       'steps', 'active_energy', 'recovery_score', 'stress_score']
        
        available_columns = [col for col in corr_columns if col in self.df.columns]
        df_corr = self.df[available_columns].select_dtypes(include=['number'])
        
        if df_corr.empty:
            print("相関を計算できるデータがありません")
            return
        
        # 相関行列を計算
        corr_matrix = df_corr.corr()
        
        # ヒートマップを作成
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
        ax.set_title('データ間の相関関係', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"グラフを保存しました: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_all_charts(self, output_dir: Path):
        """
        すべてのチャートを生成
        
        パラメータ:
        - output_dir: 出力ディレクトリ
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("グラフを生成中...")
        
        self.plot_sleep_trend(output_dir / 'sleep_trend.png')
        self.plot_hrv_trend(output_dir / 'hrv_trend.png')
        self.plot_recovery_stress_scores(output_dir / 'recovery_stress_scores.png')
        self.plot_sleep_score_detail(output_dir / 'sleep_score_detail.png')
        self.plot_activity_trend(output_dir / 'activity_trend.png')
        self.plot_correlation(output_dir / 'correlation.png')
        
        print(f"\nすべてのグラフを保存しました: {output_dir}")

