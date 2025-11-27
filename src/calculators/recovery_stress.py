"""
リカバリースコアとストレススコアの計算
"""
from typing import Optional
import numpy as np
from src.models.health_data import DailyHealth


class RecoveryStressCalculator:
    """リカバリースコアとストレススコアを計算するクラス"""
    
    def __init__(self, baseline_data: Optional[list] = None):
        """
        計算器を初期化
        
        パラメータ:
        - baseline_data: ベースライン計算用のDailyHealthオブジェクトのリスト
        """
        self.baseline_data = baseline_data or []
        self._baseline = None
        
    def calculate_baseline(self) -> dict:
        """
        ベースラインを計算（過去30日間の平均）
        
        戻り値:
        - ベースラインの辞書
        """
        if self._baseline is not None:
            return self._baseline
        
        if not self.baseline_data:
            return {}
        
        # 過去30日間のデータを使用
        recent_data = self.baseline_data[-30:] if len(self.baseline_data) > 30 else self.baseline_data
        
        hrv_values = [d.hrv_deep_sleep_avg for d in recent_data if d.hrv_deep_sleep_avg is not None]
        hr_values = [d.resting_heart_rate for d in recent_data if d.resting_heart_rate is not None]
        energy_values = [d.active_energy for d in recent_data if d.active_energy is not None]
        
        self._baseline = {
            'hrv_baseline': np.mean(hrv_values) if hrv_values else None,
            'resting_hr_baseline': np.mean(hr_values) if hr_values else None,
            'active_energy_baseline': np.mean(energy_values) if energy_values else None,
        }
        
        return self._baseline
    
    def calculate_recovery_score(self, daily_health: DailyHealth) -> Optional[int]:
        """
        リカバリースコアを計算（0-100）
        
        パラメータ:
        - daily_health: DailyHealthオブジェクト
        
        戻り値:
        - リカバリースコア（0-100）
        """
        baseline = self.calculate_baseline()
        
        # 必要なデータがない場合はNoneを返す
        if not daily_health.hrv_deep_sleep_avg and not daily_health.hrv_avg:
            return None
        
        # HRVスコア（0-40点）
        hrv_score = 0
        if daily_health.hrv_deep_sleep_avg and baseline.get('hrv_baseline'):
            hrv_ratio = daily_health.hrv_deep_sleep_avg / baseline['hrv_baseline']
            # ベースラインの80%以上で満点、50%以下で0点
            hrv_score = min(40, max(0, (hrv_ratio - 0.5) * 80))
        elif daily_health.hrv_avg and baseline.get('hrv_baseline'):
            # 深い睡眠中のHRVがない場合は、夜間平均HRVを使用
            hrv_ratio = daily_health.hrv_avg / baseline['hrv_baseline']
            hrv_score = min(40, max(0, (hrv_ratio - 0.5) * 80))
        
        # 睡眠の質スコア（0-30点）
        sleep_score = 0
        if daily_health.sleep_minutes:
            # 深い睡眠の絶対時間（最大15点）
            # 90分以上で満点、30分以下で0点
            deep_sleep_minutes = daily_health.deep_sleep_minutes or 0
            if deep_sleep_minutes >= 90:
                deep_score = 15
            elif deep_sleep_minutes >= 30:
                deep_score = (deep_sleep_minutes - 30) / 60 * 15  # 30-90分の間で線形補間
            else:
                deep_score = 0
            
            # 睡眠時間（8時間で満点、最大15点）
            sleep_hours = daily_health.total_sleep_hours or 0
            sleep_time_score = min(15, (sleep_hours / 8) * 15)
            
            sleep_score = deep_score + sleep_time_score
        
        # 安静時心拍数スコア（0-30点）
        hr_score = 0
        if daily_health.resting_heart_rate and baseline.get('resting_hr_baseline'):
            hr_ratio = baseline['resting_hr_baseline'] / daily_health.resting_heart_rate
            # ベースラインの90%以下で満点
            hr_score = min(30, max(0, (hr_ratio - 0.9) * 100))
        
        # 合計スコア
        recovery_score = hrv_score + sleep_score + hr_score
        
        return min(100, max(0, int(recovery_score)))
    
    def calculate_stress_score(self, daily_health: DailyHealth) -> Optional[int]:
        """
        ストレススコアを計算（0-100、低いほどストレス低、高いほどストレス高）
        
        パラメータ:
        - daily_health: DailyHealthオブジェクト
        
        戻り値:
        - ストレススコア（0-100）
        """
        baseline = self.calculate_baseline()
        
        # 必要なデータがない場合はNoneを返す
        if not daily_health.hrv_avg and not daily_health.resting_heart_rate:
            return None
        
        # HRV低下スコア（0-40点、高いほどストレス高）
        hrv_stress = 0
        if daily_health.hrv_avg and baseline.get('hrv_baseline'):
            hrv_ratio = daily_health.hrv_avg / baseline['hrv_baseline']
            # ベースラインより低いほどストレス高
            hrv_stress = max(0, (1.0 - hrv_ratio) * 40)
        
        # 心拍数上昇スコア（0-30点、高いほどストレス高）
        hr_stress = 0
        if daily_health.resting_heart_rate and baseline.get('resting_hr_baseline'):
            hr_ratio = daily_health.resting_heart_rate / baseline['resting_hr_baseline']
            # ベースラインより高いほどストレス高
            hr_stress = max(0, (hr_ratio - 1.0) * 30)
        
        # 睡眠の質低下スコア（0-20点、高いほどストレス高）
        sleep_stress = 0
        if daily_health.sleep_minutes:
            deep_ratio = daily_health.deep_sleep_ratio or 0
            # 深い睡眠が20%未満でストレス高
            deep_stress = max(0, (0.2 - deep_ratio) * 50)
            
            # 睡眠時間が7時間未満でストレス高
            sleep_hours = daily_health.total_sleep_hours or 0
            sleep_time_stress = max(0, (7 - sleep_hours) / 7 * 10)
            
            sleep_stress = min(20, deep_stress + sleep_time_stress)
        
        # オーバートレーニングスコア（0-10点）
        overtraining_stress = 0
        if (daily_health.active_energy and baseline.get('active_energy_baseline') and
            daily_health.hrv_avg and baseline.get('hrv_baseline')):
            energy_ratio = daily_health.active_energy / baseline['active_energy_baseline']
            hrv_ratio = daily_health.hrv_avg / baseline['hrv_baseline']
            # 活動量が多いのにHRVが低い = オーバートレーニング
            if energy_ratio > 1.2 and hrv_ratio < 0.9:
                overtraining_stress = 10
        
        # 合計スコア
        stress_score = hrv_stress + hr_stress + sleep_stress + overtraining_stress
        
        return min(100, max(0, int(stress_score)))
    
    def calculate_scores(self, daily_health: DailyHealth) -> DailyHealth:
        """
        リカバリースコアとストレススコアを計算してDailyHealthオブジェクトに設定
        
        パラメータ:
        - daily_health: DailyHealthオブジェクト
        
        戻り値:
        - スコアが設定されたDailyHealthオブジェクト
        """
        # ベースラインを更新（必要に応じて）
        if self.baseline_data:
            self._baseline = None  # 再計算を強制
        
        recovery_score = self.calculate_recovery_score(daily_health)
        stress_score = self.calculate_stress_score(daily_health)
        
        daily_health.recovery_score = recovery_score
        daily_health.stress_score = stress_score
        
        # HRVベースラインを設定
        baseline = self.calculate_baseline()
        if baseline.get('hrv_baseline'):
            daily_health.hrv_baseline = baseline['hrv_baseline']
        
        return daily_health

