from producer import Producer
from meter_generator import MeterGenerator

from datetime import datetime, timezone, timedelta
import time
import random


"""
    id: {라씨 RTU ID},
    s: 상태 
    t: 시간
    m: 미터값
    p: 현재 출력값
    mp: 현재 적용된 출력 상한값
"""

plant_capacity = [
    997.50,
    991.76,
    868.00,
    990.00,
    983.84,
    992.00,
    1997.28,
    990.00,
    451.44,
    899.76,
    499.20,
    1496.88,
    720.960,
    717.570,
    796.000,
    880.900,
    998.400,
    997.360,
    749.840,
    998.660,
    788.48,
    297.46,
    297.46,
    473.28,
    994.84,
    2087.00,
    356.40,
    678.30,
    691.22,
    362.52,
    356.40,
    2786.00,
    633.00,
    1693.00,
    489.60,
    489.60,
    994.95,
    440.64,
    627.21,
    949.00,
    756.00,
    993.24,
    993.24,
    441.00,
    924.00,
    418.50,
    837.00,
    994.95,
    325.62,
    663.30,
    781.83,
    2178.40,
    480.00,
    312.12,
    583.74,
    993.24,
    662.40,
    774.90,
    739.26,
    616.00,
    970.20,
    497.70,
    627.12,
    728.46,
    997.92,
    856.00,
    998.82,
    658.24,
    344.25,
    676.89,
    424.08,
    463.14,
    558.45,
    458.28,
    422.10,
    962.55,
    307.20,
    693.45,
    667.80,
    705.87,
    658.26,
    850.23,
    765.45,
    676.71,
    422.28,
    777.87,
    428.13,
    900.90,
    1269.45,
    1498.50,
    2002.00,
    2995.20,
    2478.00,
    2008.00,
    2995.00,
    491.00,
    994.00,
    753.00,
    981.00,
    1994.24,
]

mg = MeterGenerator()
plant_dict = {
    idx + 1: {"capacity": plant_capacity[idx], "delay": random.randint(-10, 2)}
    for idx in range(len(plant_capacity))
}

# 최소 발전량 데이터 생성
for key, value in plant_dict.items():
    capacity = value["capacity"]

    mg.set_capacity(capacity)
    efficiency_values, meter_values = mg.get_transform_meter_by_minutely()

    plant_dict[key]["efficiency_values"] = efficiency_values
    plant_dict[key]["meter_values"] = meter_values

producer = Producer()

while True:
    # Unix 타임스탬프를 일반적인 시간 형식으로 변환
    converted_time = datetime.fromtimestamp(
        int(time.time()), timezone(timedelta(hours=9))
    ).strftime("%H:%M:%S")

    hh, mm, ss = map(int, converted_time.split(":"))
    print(hh, mm, ss)

    if 0 <= ss < 10:
        print("ASDF")
        if hh == 0 and mm == 0:
            # 하루가 지나면 발전소 데이터 재생성
            for key, value in plant_dict.items():
                capacity = value["capacity"]

                mg.set_capacity(capacity)
                efficiency_values, meter_values = mg.get_transform_meter_by_minutely()

                plant_dict[key]["efficiency_values"] = efficiency_values
                plant_dict[key]["meter_values"] = meter_values

        data_list = []

        for key, value in plant_dict.items():
            total_meter = 0
            meter_values = value["meter_values"]
            efficiency_values = value["efficiency_values"]

            for idx, (meter, efficiency) in enumerate(
                zip(meter_values[: hh + 1], efficiency_values)
            ):
                if idx == hh:
                    for m, e in zip(meter[: mm + 1], efficiency):
                        total_meter = round(total_meter + m, 3)
                else:
                    total_meter += sum(meter)

            payload = {
                "id": key,
                "s": "ok",
                "t": int(time.time()) + value["delay"],
                "m": total_meter,
                "p": efficiency_values[hh][mm],
                "mp": 100,
            }

            data = {
                "schema": {
                    "type": "struct",
                    "fields": [
                        {
                            "type": "string",
                            "optional": False,
                            "doc": "HTTP Record Value",
                            "field": "value",
                        },
                        {
                            "type": "string",
                            "optional": True,
                            "doc": "HTTP Record Key",
                            "field": "key",
                        },
                        {
                            "type": "int64",
                            "optional": True,
                            "doc": "HTTP Record Timestamp",
                            "field": "timestamp",
                        },
                    ],
                },
                "payload": payload,
            }

            data_list.append(data)

        producer.send("haezoom", data_list)

    while True:
        time.sleep(1)
        converted_time = datetime.fromtimestamp(
            int(time.time()), timezone(timedelta(hours=9))
        ).strftime("%H:%M:%S")

        _hh, _mm, _ss = map(int, converted_time.split(":"))

        print(
            f"{str(hh).zfill(2)}:{str(mm).zfill(2)}",
            f"{str(_hh).zfill(2)}:{str(_mm).zfill(2)}",
        )

        if (
            f"{str(hh).zfill(2)}:{str(mm).zfill(2)}"
            < f"{str(_hh).zfill(2)}:{str(_mm).zfill(2)}"
        ):
            # 1분이 자났다면 탈출
            print("bye")
            break
