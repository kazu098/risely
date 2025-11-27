"""
健康データのモデル定義
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class DailyHealth:
    """日次の健康データ"""
    date: date
    # 睡眠データ
    sleep_minutes: Optional[int] = None
    deep_sleep_minutes: Optional[int] = None
    rem_sleep_minutes: Optional[int] = None
    light_sleep_minutes: Optional[int] = None
    # HRVデータ
    hrv_avg: Optional[float] = None
    hrv_deep_sleep_avg: Optional[float] = None
    hrv_deep_sleep_stddev: Optional[float] = None
    hrv_min: Optional[float] = None
    hrv_max: Optional[float] = None
    hrv_baseline: Optional[float] = None
    # 心拍数データ
    resting_heart_rate: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    # 活動データ
    steps: Optional[int] = None
    active_energy: Optional[float] = None
    # 計算されたスコア
    recovery_score: Optional[int] = None
    stress_score: Optional[int] = None
    sleep_score: Optional[int] = None

    @property
    def deep_sleep_ratio(self) -> Optional[float]:
        """深い睡眠の割合"""
        if self.sleep_minutes and self.deep_sleep_minutes:
            return self.deep_sleep_minutes / self.sleep_minutes
        return None

    @property
    def total_sleep_hours(self) -> Optional[float]:
        """総睡眠時間（時間）"""
        if self.sleep_minutes:
            return self.sleep_minutes / 60.0
        return None

