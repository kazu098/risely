# リカバリースコアとストレススコアの計算方法

## 概要

Apple Healthから取得できるデータを使って、**リカバリースコア**と**ストレススコア**を日単位で計算・表示する方法。

---

## リカバリースコア（Recovery Score）

### HRVを主要指標として使用

**HRV（心拍変動）はリカバリースコアの最も重要な指標**です。

特に**深い睡眠中のHRV**が重要：
- 深い睡眠中は副交感神経が優位になり、HRVが高くなる
- 深い睡眠中のHRVが高い = 回復が良好
- 深い睡眠中のHRVの分散（標準偏差）も回復状態を反映

### 計算に使用するデータ

1. **深い睡眠中のHRV平均値**（最重要）
   - Apple Healthから取得: `HeartRateVariabilitySDNN` + 睡眠ステージ（深い睡眠）
   - 高いほど回復良好

2. **HRVのベースラインからの乖離度**
   - 個人の過去30日のHRV平均をベースラインとして計算
   - ベースラインより高い = 回復良好
   - ベースラインより低い = 回復不良

3. **睡眠の質**
   - 深い睡眠の割合（総睡眠時間に対する割合）
   - 総睡眠時間
   - 睡眠の連続性（覚醒回数）

4. **安静時心拍数**
   - 低いほど回復良好
   - ベースラインより低い = 回復良好

### 計算式（簡易版）

```python
def calculate_recovery_score(hrv_deep_sleep_avg, hrv_baseline, 
                             deep_sleep_ratio, total_sleep_minutes,
                             resting_hr, resting_hr_baseline):
    """
    リカバリースコアを計算（0-100）
    
    パラメータ:
    - hrv_deep_sleep_avg: 深い睡眠中のHRV平均値
    - hrv_baseline: 個人のHRVベースライン（過去30日の平均）
    - deep_sleep_ratio: 深い睡眠の割合（0-1）
    - total_sleep_minutes: 総睡眠時間（分）
    - resting_hr: 安静時心拍数
    - resting_hr_baseline: 個人の安静時心拍数ベースライン
    """
    # HRVスコア（0-40点）
    hrv_ratio = hrv_deep_sleep_avg / hrv_baseline if hrv_baseline > 0 else 1.0
    hrv_score = min(40, max(0, (hrv_ratio - 0.8) * 100))  # ベースラインの80%以上で満点
    
    # 睡眠の質スコア（0-30点）
    sleep_quality_score = (
        min(15, (deep_sleep_ratio * 30)) +  # 深い睡眠の割合（最大15点）
        min(15, (total_sleep_minutes / 8 * 15))  # 睡眠時間（8時間で満点、最大15点）
    )
    
    # 安静時心拍数スコア（0-30点）
    hr_ratio = resting_hr_baseline / resting_hr if resting_hr > 0 else 1.0
    hr_score = min(30, max(0, (hr_ratio - 0.9) * 100))  # ベースラインの90%以下で満点
    
    # 合計スコア
    recovery_score = hrv_score + sleep_quality_score + hr_score
    
    return min(100, max(0, int(recovery_score)))
```

### ベースラインの計算

```python
def calculate_baseline(df, days=30):
    """
    過去N日間のデータからベースラインを計算
    """
    recent_data = df.tail(days)
    
    baseline = {
        'hrv_baseline': recent_data['hrv_deep_sleep_avg'].mean(),
        'resting_hr_baseline': recent_data['resting_heart_rate'].mean(),
    }
    
    return baseline
```

---

## ストレススコア（Stress Score）

### HRVと心拍数を基に計算

**ストレススコアは日単位で表示可能**です。

### 計算に使用するデータ

1. **HRVの低下度**
   - ベースラインより低い = ストレス高
   - HRVが低い = 交感神経が優位 = ストレス状態

2. **心拍数の上昇度**
   - ベースラインより高い = ストレス高
   - 安静時心拍数が高い = ストレス状態

3. **睡眠の質の低下**
   - 深い睡眠が少ない = ストレス高
   - 睡眠時間が短い = ストレス高

4. **活動量とのバランス**
   - 活動量が多いのにHRVが低い = オーバートレーニング = ストレス高

### 計算式（簡易版）

```python
def calculate_stress_score(hrv_avg, hrv_baseline,
                          resting_hr, resting_hr_baseline,
                          deep_sleep_ratio, total_sleep_minutes,
                          active_energy, active_energy_baseline):
    """
    ストレススコアを計算（0-100、低いほどストレス低、高いほどストレス高）
    
    パラメータ:
    - hrv_avg: 日中のHRV平均値（または夜間平均）
    - hrv_baseline: HRVベースライン
    - resting_hr: 安静時心拍数
    - resting_hr_baseline: 安静時心拍数ベースライン
    - deep_sleep_ratio: 深い睡眠の割合
    - total_sleep_minutes: 総睡眠時間
    - active_energy: アクティブエネルギー
    - active_energy_baseline: アクティブエネルギーベースライン
    """
    # HRV低下スコア（0-40点、高いほどストレス高）
    hrv_ratio = hrv_avg / hrv_baseline if hrv_baseline > 0 else 1.0
    hrv_stress = max(0, (1.0 - hrv_ratio) * 40)  # ベースラインより低いほどストレス高
    
    # 心拍数上昇スコア（0-30点、高いほどストレス高）
    hr_ratio = resting_hr / resting_hr_baseline if resting_hr_baseline > 0 else 1.0
    hr_stress = max(0, (hr_ratio - 1.0) * 30)  # ベースラインより高いほどストレス高
    
    # 睡眠の質低下スコア（0-20点、高いほどストレス高）
    sleep_stress = (
        max(0, (0.2 - deep_sleep_ratio) * 50) +  # 深い睡眠が20%未満でストレス高
        max(0, (7 * 60 - total_sleep_minutes) / (7 * 60) * 10)  # 睡眠時間が7時間未満でストレス高
    )
    sleep_stress = min(20, sleep_stress)
    
    # オーバートレーニングスコア（0-10点）
    # 活動量が多いのにHRVが低い = ストレス高
    if active_energy > active_energy_baseline * 1.2 and hrv_ratio < 0.9:
        overtraining_stress = 10
    else:
        overtraining_stress = 0
    
    # 合計スコア
    stress_score = hrv_stress + hr_stress + sleep_stress + overtraining_stress
    
    return min(100, max(0, int(stress_score)))
```

---

## Apple Healthからのデータ取得

### 必要なデータタイプ

1. **HeartRateVariabilitySDNN**
   - HRVの値（ミリ秒単位）
   - タイムスタンプ付きで取得
   - 睡眠ステージと組み合わせて「深い睡眠中のHRV」を抽出

2. **SleepAnalysis**
   - 睡眠ステージ（深い睡眠、REM、浅い睡眠、覚醒）
   - タイムスタンプ付き

3. **HeartRate**
   - 心拍数
   - 安静時心拍数を抽出（睡眠中または安静時の最小値）

4. **ActiveEnergyBurned**
   - アクティブエネルギー
   - 1日の合計

### データのマッチング

```python
def extract_deep_sleep_hrv(hrv_data, sleep_data):
    """
    深い睡眠中のHRVを抽出
    
    パラメータ:
    - hrv_data: HRVデータ（タイムスタンプ、値）
    - sleep_data: 睡眠データ（タイムスタンプ、ステージ）
    """
    deep_sleep_periods = sleep_data[sleep_data['stage'] == 'deep']
    
    deep_sleep_hrv = []
    for _, sleep_period in deep_sleep_periods.iterrows():
        start = sleep_period['start']
        end = sleep_period['end']
        
        # この期間内のHRVデータを抽出
        period_hrv = hrv_data[
            (hrv_data['timestamp'] >= start) & 
            (hrv_data['timestamp'] <= end)
        ]
        
        deep_sleep_hrv.extend(period_hrv['value'].tolist())
    
    return {
        'avg': np.mean(deep_sleep_hrv) if deep_sleep_hrv else None,
        'stddev': np.std(deep_sleep_hrv) if deep_sleep_hrv else None,
        'min': np.min(deep_sleep_hrv) if deep_sleep_hrv else None,
        'max': np.max(deep_sleep_hrv) if deep_sleep_hrv else None,
    }
```

---

## 実装の優先順位

### Phase 1: 基本的なHRV分析

1. ✅ 夜間HRV平均値の計算
2. ✅ 深い睡眠中のHRV平均値の計算
3. ✅ ベースラインの計算（過去30日の平均）

### Phase 2: リカバリースコアの計算

1. ✅ リカバリースコアの計算式実装
2. ✅ 日単位でのスコア表示
3. ✅ 週次・月次のトレンド可視化

### Phase 3: ストレススコアの計算

1. ✅ ストレススコアの計算式実装
2. ✅ 日単位でのスコア表示
3. ✅ リカバリースコアとの相関分析

---

## 注意点

1. **個人差が大きい**
   - HRVは個人差が非常に大きい
   - 必ず個人のベースラインと比較する
   - 絶対値ではなく、ベースラインからの乖離度を使用

2. **ベースラインの更新**
   - ベースラインは定期的に更新（例：過去30日のローリング平均）
   - 季節変動や体調変化を考慮

3. **データの品質**
   - Apple Watchの装着状況によってデータの品質が変わる
   - データが少ない日はスコアを計算しない、または信頼度を表示

4. **段階的な実装**
   - 最初は簡易版の計算式で開始
   - データが蓄積されたら、より精密なモデルに改善

---

## 参考

- Oura RingのReadiness Score: HRV、睡眠、活動量を組み合わせ
- GarminのRecovery Score: HRVステータスを主要指標として使用
- WhoopのRecovery Score: HRV、睡眠、心拍数を組み合わせ

