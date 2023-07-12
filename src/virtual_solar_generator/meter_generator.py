import random
from efficiency_generator import EfficiencyGenerator
import time


class MeterGenerator:
    def __init__(self):
        self.capacity = 1500
        self.eg = EfficiencyGenerator()

    def __get_efficiency(self):
        return self.eg.get_efficiency()

    def __get_meter_by_hourly(self):
        meter = [self.capacity] * 24

        efficiency = self.__get_efficiency()

        for t in range(24):
            meter[t] = round(meter[t] * efficiency[t] / 100, 3)

        return efficiency, meter

    def set_capacity(self, capacity):
        self.capacity = capacity

    def get_transform_meter_by_minutely(self):
        efficiency, meter = self.__get_meter_by_hourly()

        # 1분 단위 발전량을 저장할 리스트
        meter_values = []
        efficiency_values = []

        for e, m in zip(efficiency, meter):
            if e == 0:
                meter_values.append([0] * 60)
                efficiency_values.append([0] * 60)
                continue
            # 효율 편차 - 20%
            deviation = round(e * 0.2, 3)

            # 1분 단위 발전량을 저장할 리스트
            meter_minute_values = []
            efficiency_minute_values = []

            # 시간 동안의 발전량을 60으로 나누어 1분 단위 발전량을 생성
            average_generation = round(m / 60, 3)
            for _ in range(60):
                # 랜덤한 값을 생성하여 리스트에 추가
                efficiency_minute_values.append(
                    round(random.uniform(e - deviation, e + deviation), 3)
                )

                meter_minute_values.append(
                    round(average_generation * (efficiency_minute_values[-1] / e), 3)
                )

            meter_values.append(meter_minute_values)
            efficiency_values.append(efficiency_minute_values)

        return efficiency_values, meter_values
