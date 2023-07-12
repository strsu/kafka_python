import random


class EfficiencyGenerator:
    def __init__(self):
        self.solar_power = [
            0,
            0,
            0,
            0,
            0,
            0,  # 5
            10,
            20,
            40,
            50,  # 9
            70,
            80,
            100,
            90,  # 13
            80,
            70,
            50,
            40,  # 17
            30,
            20,
            0,
            0,
            0,
            0,
        ]  # 태양의 세기

        self.time_serize = [5, 9, 13, 17]

    def __disturb_solar(self, t, start, end):
        value = self.solar_power[t : t + 4]
        for i in range(4):
            r = random.randrange(start, end) / 100
            value[i] = round(value[i] * r, 3)
        return value

    def clean(self, t):
        # 맑음, 0 ~ 10%의 태양 세기 경감
        return self.__disturb_solar(t, 0, 10)

    def rain(self, t):
        # 비, 60 ~ 80%의 태양 세기 경감
        return self.__disturb_solar(t, 60, 80)

    def snow(self, t):
        # 눈, 40 ~ 60%의 태양 세기 경감
        return self.__disturb_solar(t, 40, 60)

    def cloud(self, t):
        # 구름, 50 ~ 80%의 태양 세기 경감
        return self.__disturb_solar(t, 50, 80)

    def pickup_weather(self):
        r = random.randint(1, 4)

        weather = self.clean

        if r == 2:
            weather = self.rain
        elif r == 3:
            weather = self.snow
        elif r == 4:
            weather = self.cloud

        return weather

    def get_efficiency(self):
        efficiency = [0] * 24
        for t in self.time_serize:
            weather = self.pickup_weather()
            efficiency[t : t + 4] = weather(t)

        return efficiency
