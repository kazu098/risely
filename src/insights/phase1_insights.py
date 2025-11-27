"""
Phase 1のインサイト生成
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import date, timedelta


class Phase1Insights:
    """Phase 1のインサイトを生成するクラス"""
    
    def __init__(self, df: pd.DataFrame):
        """
        インサイト生成器を初期化
        
        パラメータ:
        - df: 日次健康データのDataFrame
        """
        self.df = df.copy()
        if 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
            self.df = self.df.sort_values('date')
            self.df['weekday'] = self.df['date'].dt.day_name()
    
    def detect_weekly_pattern(self) -> Dict[str, str]:
        """
        週次パターンを検出
        
        戻り値:
        - インサイトの辞書
        """
        insights = {}
        
        if 'recovery_score' not in self.df.columns:
            return insights
        
        # 曜日ごとのリカバリースコア平均
        weekly_avg = self.df.groupby('weekday')['recovery_score'].mean()
        
        if weekly_avg.empty:
            return insights
        
        lowest_day = weekly_avg.idxmin()
        highest_day = weekly_avg.idxmax()
        
        insights['weekly_pattern'] = (
            f"過去{len(self.df)}日間で、{lowest_day}のリカバリースコアが最も低く"
            f"（平均{weekly_avg[lowest_day]:.0f}pt）、{highest_day}が最も高い"
            f"（平均{weekly_avg[highest_day]:.0f}pt）傾向があります。"
        )
        
        return insights
    
    def detect_sleep_hrv_correlation(self) -> Dict[str, str]:
        """
        睡眠の質とHRVの関係を検出
        
        戻り値:
        - インサイトの辞書
        """
        insights = {}
        
        # 深い睡眠の絶対時間（分）とHRVの相関
        if 'deep_sleep_minutes' in self.df.columns and 'hrv_avg' in self.df.columns:
            valid_data = self.df[['deep_sleep_minutes', 'hrv_avg']].dropna()
            if len(valid_data) > 10:
                corr = valid_data['deep_sleep_minutes'].corr(valid_data['hrv_avg'])
                
                if corr > 0.3:
                    insights['sleep_hrv_correlation'] = (
                        f"深い睡眠の時間とHRVには強い正の相関があります（相関係数: {corr:.2f}）。"
                        f"深い睡眠を増やすことで、HRVの向上が期待できます。"
                    )
                elif corr < -0.3:
                    insights['sleep_hrv_correlation'] = (
                        f"深い睡眠の時間とHRVには負の相関があります（相関係数: {corr:.2f}）。"
                        f"他の要因も影響している可能性があります。"
                    )
        
        # 同じ睡眠時間でも深い睡眠の時間が違うとHRVが変動
        if 'sleep_minutes' in self.df.columns and 'deep_sleep_minutes' in self.df.columns and 'hrv_avg' in self.df.columns:
            # 睡眠時間が7時間前後の日を抽出
            sleep_7h = self.df[
                (self.df['sleep_minutes'] >= 6.5 * 60) & 
                (self.df['sleep_minutes'] <= 7.5 * 60)
            ].copy()
            
            if len(sleep_7h) > 5:
                # 深い睡眠の時間（分）でグループ化
                sleep_7h['deep_time_bin'] = pd.cut(
                    sleep_7h['deep_sleep_minutes'],
                    bins=[0, 30, 45, 60, 90, float('inf')],
                    labels=['低（30分未満）', '中（30-45分）', '高（45-60分）', '非常に高（60-90分）', '最高（90分以上）']
                )
                
                hrv_by_deep = sleep_7h.groupby('deep_time_bin', observed=True)['hrv_avg'].mean()
                
                if len(hrv_by_deep) > 1:
                    max_hrv = hrv_by_deep.max()
                    min_hrv = hrv_by_deep.min()
                    diff_pct = ((max_hrv - min_hrv) / min_hrv * 100) if min_hrv > 0 else 0
                    
                    insights['sleep_time_hrv_variation'] = (
                        f"同じ睡眠時間（7時間前後）でも、深い睡眠の時間が30分違うだけで"
                        f"HRVが約{diff_pct:.0f}%変動しています。"
                        f"睡眠時間だけでなく、深い睡眠の絶対時間も重要です。"
                    )
        
        return insights
    
    def detect_activity_recovery_relationship(self) -> Dict[str, str]:
        """
        活動量と回復の関係を検出
        
        戻り値:
        - インサイトの辞書
        """
        insights = {}
        
        # 歩数と翌日の深い睡眠の関係
        if 'steps' in self.df.columns and 'deep_sleep_minutes' in self.df.columns:
            self.df['next_day_deep_sleep'] = self.df['deep_sleep_minutes'].shift(-1)
            
            # 歩数でグループ化
            self.df['steps_category'] = pd.cut(
                self.df['steps'],
                bins=[0, 5000, 8000, 10000, float('inf')],
                labels=['低（5000歩未満）', '中（5000-8000歩）', '高（8000-10000歩）', '非常に高（10000歩以上）']
            )
            
            steps_deep_sleep = self.df.groupby('steps_category', observed=True)['next_day_deep_sleep'].mean()
            
            if len(steps_deep_sleep) > 1 and steps_deep_sleep.notna().any():
                max_category = steps_deep_sleep.idxmax()
                max_value = steps_deep_sleep.max()
                
                if pd.notna(max_value):
                    insights['steps_deep_sleep'] = (
                        f"歩数が{max_category}の日の翌日は、深い睡眠が平均{max_value:.0f}分と"
                        f"最も多くなっています。適度な運動が睡眠の質を向上させています。"
                    )
        
        # アクティブエネルギーと翌日のHRVの関係
        if 'active_energy' in self.df.columns and 'hrv_avg' in self.df.columns:
            self.df['next_day_hrv'] = self.df['hrv_avg'].shift(-1)
            
            # アクティブエネルギーでグループ化
            energy_median = self.df['active_energy'].median()
            high_energy = self.df[self.df['active_energy'] > energy_median * 1.2]
            low_energy = self.df[self.df['active_energy'] < energy_median * 0.8]
            
            if len(high_energy) > 5 and len(low_energy) > 5:
                high_hrv = high_energy['next_day_hrv'].mean()
                low_hrv = low_energy['next_day_hrv'].mean()
                
                if pd.notna(high_hrv) and pd.notna(low_hrv):
                    diff_pct = ((low_hrv - high_hrv) / high_hrv * 100) if high_hrv > 0 else 0
                    
                    if diff_pct < -5:  # 高エネルギー日の翌日がHRV低い
                        insights['overtraining'] = (
                            f"アクティブエネルギーが高い日の翌日は、HRVが平均{diff_pct:.0f}%低下しています。"
                            f"オーバートレーニングの可能性があります。適度な休息を取ることをお勧めします。"
                        )
        
        return insights
    
    def detect_anomalies(self) -> Dict[str, str]:
        """
        異常値を検出
        
        戻り値:
        - インサイトの辞書
        """
        insights = {}
        
        # 最新日のデータを取得
        if self.df.empty:
            return insights
        
        latest = self.df.iloc[-1]
        
        # HRVがベースラインより25%以上低い
        if 'hrv_avg' in latest and 'hrv_baseline' in latest:
            if pd.notna(latest['hrv_avg']) and pd.notna(latest['hrv_baseline']):
                hrv_ratio = latest['hrv_avg'] / latest['hrv_baseline']
                if hrv_ratio < 0.75:
                    insights['low_hrv_alert'] = (
                        f"昨日のHRVが過去30日の平均より{((1-hrv_ratio)*100):.0f}%低く、"
                        f"リカバリースコアが{latest.get('recovery_score', 'N/A')}ptでした。"
                        f"今日は休息を優先することをお勧めします。"
                    )
        
        # 深い睡眠が30分未満の日が3日連続
        if 'deep_sleep_minutes' in self.df.columns:
            recent = self.df.tail(3)
            low_deep_sleep = recent[recent['deep_sleep_minutes'] < 30]
            
            if len(low_deep_sleep) >= 3:
                insights['low_deep_sleep_alert'] = (
                    f"深い睡眠が30分未満の日が3日連続しています。"
                    f"睡眠の質を改善する対策を検討してください。"
                )
        
        return insights
    
    def detect_optimal_sleep_time(self) -> Dict[str, str]:
        """
        最適な睡眠時間を検出
        
        戻り値:
        - インサイトの辞書
        """
        insights = {}
        
        if 'sleep_minutes' not in self.df.columns or 'recovery_score' not in self.df.columns:
            return insights
        
        # 睡眠時間ごとにリカバリースコアを集計
        self.df['sleep_hours'] = self.df['sleep_minutes'] / 60
        self.df['sleep_hour_bin'] = pd.cut(
            self.df['sleep_hours'],
            bins=[0, 6, 6.5, 7, 7.5, 8, 8.5, 9, float('inf')],
            labels=['6h未満', '6-6.5h', '6.5-7h', '7-7.5h', '7.5-8h', '8-8.5h', '8.5-9h', '9h以上']
        )
        
        sleep_recovery = self.df.groupby('sleep_hour_bin', observed=True)['recovery_score'].mean()
        
        if len(sleep_recovery) > 1 and sleep_recovery.notna().any():
            optimal_bin = sleep_recovery.idxmax()
            optimal_score = sleep_recovery.max()
            
            if pd.notna(optimal_score):
                insights['optimal_sleep_time'] = (
                    f"あなたの最適な睡眠時間は{optimal_bin}です。"
                    f"この時間に近い日のリカバリースコアが最も高くなっています（平均{optimal_score:.0f}pt）。"
                )
        
        return insights
    
    def generate_weekly_insights(self) -> List[str]:
        """
        週次インサイトを生成
        
        戻り値:
        - インサイトのリスト
        """
        all_insights = []
        
        # 各インサイトを生成
        weekly_pattern = self.detect_weekly_pattern()
        all_insights.extend(weekly_pattern.values())
        
        sleep_hrv = self.detect_sleep_hrv_correlation()
        all_insights.extend(sleep_hrv.values())
        
        activity_recovery = self.detect_activity_recovery_relationship()
        all_insights.extend(activity_recovery.values())
        
        optimal_sleep = self.detect_optimal_sleep_time()
        all_insights.extend(optimal_sleep.values())
        
        anomalies = self.detect_anomalies()
        all_insights.extend(anomalies.values())
        
        return all_insights
    
    def format_weekly_report(self) -> str:
        """
        週次レポートをフォーマット
        
        戻り値:
        - フォーマットされたレポート文字列
        """
        insights = self.generate_weekly_insights()
        
        if not insights:
            return "データが不足しているため、インサイトを生成できませんでした。"
        
        report = "【先週のあなたのパターン】\n\n"
        
        for i, insight in enumerate(insights, 1):
            report += f"{i}. {insight}\n\n"
        
        return report

