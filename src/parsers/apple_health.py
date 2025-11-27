"""
Apple Health XMLデータのパーサー
"""
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from dateutil import parser as date_parser


class AppleHealthParser:
    """Apple Health XMLファイルをパースするクラス"""
    
    # 必要なデータタイプ
    DATA_TYPES = {
        'sleep': 'HKCategoryTypeIdentifierSleepAnalysis',
        'hrv': 'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
        'heart_rate': 'HKQuantityTypeIdentifierHeartRate',
        'resting_heart_rate': 'HKQuantityTypeIdentifierRestingHeartRate',
        'steps': 'HKQuantityTypeIdentifierStepCount',
        'active_energy': 'HKQuantityTypeIdentifierActiveEnergyBurned',
    }
    
    # ワークアウトタイプのマッピング
    WORKOUT_TYPES = {
        'HKWorkoutActivityTypeRunning': 'running',
        'HKWorkoutActivityTypeCycling': 'cycling',
        'HKWorkoutActivityTypeWalking': 'walking',
        'HKWorkoutActivityTypeSwimming': 'swimming',
        'HKWorkoutActivityTypeElliptical': 'elliptical',
        'HKWorkoutActivityTypeTraditionalStrengthTraining': 'strength',
        'HKWorkoutActivityTypeYoga': 'yoga',
        'HKWorkoutActivityTypeCoreTraining': 'core',
        'HKWorkoutActivityTypeFlexibility': 'flexibility',
    }
    
    # 睡眠ステージのマッピング
    SLEEP_STAGES = {
        'HKCategoryValueSleepAnalysisAsleepUnspecified': 'unspecified',
        'HKCategoryValueSleepAnalysisAsleepCore': 'light',
        'HKCategoryValueSleepAnalysisAsleepDeep': 'deep',
        'HKCategoryValueSleepAnalysisAsleepREM': 'rem',
        'HKCategoryValueSleepAnalysisAwake': 'awake',
    }
    
    def __init__(self, xml_path: str):
        """
        パーサーを初期化
        
        パラメータ:
        - xml_path: Apple Health XMLファイルのパス
        """
        self.xml_path = xml_path
        self.tree = None
        self.root = None
        
    def parse(self):
        """XMLファイルをパース"""
        print(f"XMLファイルを読み込み中: {self.xml_path}")
        self.tree = ET.parse(self.xml_path)
        self.root = self.tree.getroot()
        print("XMLファイルの読み込み完了")
        
    def extract_records(self, data_type: str) -> List[Dict]:
        """
        指定されたデータタイプのレコードを抽出
        
        パラメータ:
        - data_type: データタイプ（'sleep', 'hrv', 'heart_rate'など）
        
        戻り値:
        - レコードのリスト
        """
        if not self.root:
            raise ValueError("XMLファイルを先にパースしてください")
        
        type_identifier = self.DATA_TYPES.get(data_type)
        if not type_identifier:
            raise ValueError(f"不明なデータタイプ: {data_type}")
        
        records = []
        for record in self.root.findall('.//Record'):
            if record.get('type') == type_identifier:
                record_data = {
                    'type': data_type,
                    'source': record.get('sourceName', ''),
                    'value': record.get('value'),
                    'unit': record.get('unit', ''),
                    'start_date': record.get('startDate'),
                    'end_date': record.get('endDate'),
                }
                
                # 睡眠データの場合、ステージも取得
                if data_type == 'sleep':
                    record_data['stage'] = self.SLEEP_STAGES.get(
                        record.get('value', ''), 
                        'unknown'
                    )
                
                records.append(record_data)
        
        print(f"{data_type}: {len(records)}件のレコードを抽出")
        return records
    
    def extract_workouts(self) -> List[Dict]:
        """
        ワークアウトデータを抽出
        
        戻り値:
        - ワークアウトレコードのリスト
        """
        if not self.root:
            raise ValueError("XMLファイルを先にパースしてください")
        
        workouts = []
        for workout in self.root.findall('.//Workout'):
            workout_type = workout.get('workoutActivityType', '')
            workout_name = self.WORKOUT_TYPES.get(workout_type, workout_type)
            
            workout_data = {
                'type': workout_name,
                'type_identifier': workout_type,
                'start_date': workout.get('startDate'),
                'end_date': workout.get('endDate'),
                'duration': workout.get('duration'),
                'total_energy_burned': workout.get('totalEnergyBurned'),
                'total_distance': workout.get('totalDistance'),
            }
            
            # メタデータから追加情報を取得
            metadata = {}
            for metadata_entry in workout.findall('.//MetadataEntry'):
                key = metadata_entry.get('key')
                value = metadata_entry.get('value')
                if key and value:
                    metadata[key] = value
            
            workout_data['metadata'] = metadata
            workouts.append(workout_data)
        
        print(f"workouts: {len(workouts)}件のレコードを抽出")
        return workouts
    
    def extract_all_data(self) -> Dict[str, List[Dict]]:
        """
        すべてのデータタイプを抽出
        
        戻り値:
        - データタイプごとのレコードの辞書
        """
        all_data = {}
        for data_type in self.DATA_TYPES.keys():
            try:
                all_data[data_type] = self.extract_records(data_type)
            except Exception as e:
                print(f"警告: {data_type}の抽出中にエラーが発生: {e}")
                all_data[data_type] = []
        
        # ワークアウトデータも追加
        try:
            all_data['workouts'] = self.extract_workouts()
        except Exception as e:
            print(f"警告: workoutsの抽出中にエラーが発生: {e}")
            all_data['workouts'] = []
        
        return all_data
    
    def to_dataframes(self) -> Dict[str, pd.DataFrame]:
        """
        抽出したデータをDataFrameに変換
        
        戻り値:
        - データタイプごとのDataFrameの辞書
        """
        all_data = self.extract_all_data()
        dataframes = {}
        
        for data_type, records in all_data.items():
            if records:
                df = pd.DataFrame(records)
                # 日付をパース
                if 'start_date' in df.columns:
                    df['start_date'] = pd.to_datetime(df['start_date'])
                if 'end_date' in df.columns:
                    df['end_date'] = pd.to_datetime(df['end_date'])
                # 値を数値に変換
                if 'value' in df.columns:
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                # ワークアウトのdurationとtotal_energy_burnedを数値に変換
                if 'duration' in df.columns:
                    df['duration'] = pd.to_numeric(df['duration'], errors='coerce')
                if 'total_energy_burned' in df.columns:
                    df['total_energy_burned'] = pd.to_numeric(df['total_energy_burned'], errors='coerce')
                if 'total_distance' in df.columns:
                    df['total_distance'] = pd.to_numeric(df['total_distance'], errors='coerce')
                
                dataframes[data_type] = df
            else:
                dataframes[data_type] = pd.DataFrame()
        
        return dataframes

