"""
睡眠スコアの計算
"""
from typing import Optional
from src.models.health_data import DailyHealth


class SleepScoreCalculator:
    """睡眠スコアを計算するクラス"""
    
    def calculate_sleep_score(self, daily_health: DailyHealth) -> Optional[int]:
        """
        睡眠スコアを計算（0-100）
        
        パラメータ:
        - daily_health: DailyHealthオブジェクト
        
        戻り値:
        - 睡眠スコア（0-100）
        """
        if not daily_health.sleep_minutes:
            return None
        
        # 1. 総睡眠時間スコア（0-40点）
        sleep_hours = daily_health.total_sleep_hours or 0
        if sleep_hours >= 8:
            sleep_time_score = 40
        elif sleep_hours >= 7:
            # 7-8時間の間で線形補間
            sleep_time_score = 20 + (sleep_hours - 7) * 20
        elif sleep_hours >= 6:
            # 6-7時間の間で線形補間
            sleep_time_score = (sleep_hours - 6) * 20
        else:
            sleep_time_score = 0
        
        # 2. 深い睡眠の絶対時間スコア（0-35点）
        deep_sleep_minutes = daily_health.deep_sleep_minutes or 0
        if deep_sleep_minutes >= 90:
            deep_sleep_score = 35
        elif deep_sleep_minutes >= 60:
            # 60-90分の間で線形補間
            deep_sleep_score = 20 + (deep_sleep_minutes - 60) / 30 * 15
        elif deep_sleep_minutes >= 30:
            # 30-60分の間で線形補間
            deep_sleep_score = (deep_sleep_minutes - 30) / 30 * 20
        else:
            deep_sleep_score = 0
        
        # 3. REM睡眠スコア（0-15点）
        rem_sleep_minutes = daily_health.rem_sleep_minutes or 0
        if rem_sleep_minutes >= 120:
            rem_sleep_score = 15
        elif rem_sleep_minutes >= 90:
            # 90-120分の間で線形補間
            rem_sleep_score = 10 + (rem_sleep_minutes - 90) / 30 * 5
        elif rem_sleep_minutes >= 60:
            # 60-90分の間で線形補間
            rem_sleep_score = (rem_sleep_minutes - 60) / 30 * 10
        else:
            rem_sleep_score = 0
        
        # 4. 睡眠の連続性スコア（0-10点）
        # 浅い睡眠と深い睡眠のバランス
        light_sleep_minutes = daily_health.light_sleep_minutes or 0
        total_sleep = daily_health.sleep_minutes
        
        if total_sleep > 0:
            # 深い睡眠の割合が適切（15-25%）なら満点
            deep_ratio = deep_sleep_minutes / total_sleep
            if 0.15 <= deep_ratio <= 0.25:
                continuity_score = 10
            elif 0.10 <= deep_ratio < 0.15 or 0.25 < deep_ratio <= 0.30:
                continuity_score = 7
            elif 0.05 <= deep_ratio < 0.10 or 0.30 < deep_ratio <= 0.35:
                continuity_score = 5
            else:
                continuity_score = 2
        else:
            continuity_score = 0
        
        # 合計スコア
        sleep_score = sleep_time_score + deep_sleep_score + rem_sleep_score + continuity_score
        
        return min(100, max(0, int(sleep_score)))

