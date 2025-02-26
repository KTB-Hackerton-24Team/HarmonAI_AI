import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import os

class wheather:
    def __init__(self, si, gu):
        data = pd.read_excel('./location_grids.xlsx')

        self.serviceKey = "GqEWtRiEG86%2BLC9zwqeHkFi42baLKX19W1WXnsGTykoDeqoYnmxQiBa6nuAPKDDN%2F2cIdOcr%2B9yfl4fS2q8LGg%3D%3D"
        now = datetime.now()

        self.base_date = now.strftime("%Y%m%d")
        base_time = now.strftime("%H%M")
        self.si = si
        self.gu = gu
        grid = data[(data['1단계'] == self.si) & (data['2단계'] == self.gu)]
        if not grid.empty:
            self.nx = f"{grid.iloc[0]['격자 X']}"
            print(self.nx)
            self.ny = f"{grid.iloc[0]['격자 Y']}"
            print(self.ny)

        else:
            print(f"{self.si} {self.gu}가 존재하지 않습니다.")
            print("서울특별시 종로구 날씨를 출력합니다.")
            self.nx = '60'
            self.ny = '127'


        input_d = datetime.strptime(self.base_date + base_time, "%Y%m%d%H%M") - timedelta(hours = 1)
        input_datetime = input_d.strftime("%Y%m%d%H%M")

        input_date = input_datetime[:-4]
        input_time = input_datetime[-4:]

        self.url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst?serviceKey={self.serviceKey}&numOfRows=60&pageNo=1&dataType=json&base_date={self.base_date}&base_time={base_time}&nx={self.nx}&ny={self.ny}"

        self.deg_code = {0 : 'N', 360 : 'N', 180 : 'S', 270 : 'W', 90 : 'E', 22.5 :'NNE',
           45 : 'NE', 67.5 : 'ENE', 112.5 : 'ESE', 135 : 'SE', 157.5 : 'SSE',
           202.5 : 'SSW', 225 : 'SW', 247.5 : 'WSW', 292.5 : 'WNW', 315 : 'NW',
           337.5 : 'NNW'}

        self.pyt_code = {0 : '강수 없음', 1 : '비', 2 : '비/눈', 3 : '눈', 5 : '빗방울', 6 : '진눈깨비', 7 : '눈날림'}
        self.sky_code = {1 : '맑음', 3 : '구름많음', 4 : '흐림'}

    def get_info(self):
        response = requests.get(self.url, verify=False)
        res = json.loads(response.text)

        informations = dict()
        for items in res['response']['body']['items']['item'] :
            cate = items['category']
            fcstTime = items['fcstTime']
            fcstValue = items['fcstValue']
            temp = dict()
            temp[cate] = fcstValue

            if fcstTime not in informations.keys() :
                informations[fcstTime] = dict()
            informations[fcstTime][cate] = fcstValue

        key = list(informations.keys())[-1]
        val = informations[key]

        return key, val

    def __call__(self):
        key, val = self.get_info()

        template = f"""{self.base_date[:4]}년 {self.base_date[4:6]}월 {self.base_date[-2:]}일 {key[:2]}시 {key[2:]}분 {(int(self.nx), int(self.ny))} 지역의 날씨는 """

        if val['SKY']:
            sky_temp = self.sky_code[int(val['SKY'])]
            template += sky_temp + " "

        if val['PTY'] :
            pty_temp = self.pyt_code[int(val['PTY'])]
            template += pty_temp
            if val['RN1'] != '강수없음' :
                rn1_temp = val['RN1']
                template += f"시간당 {rn1_temp}mm "

        if val['T1H'] :
            t1h_temp = float(val['T1H'])
            template += f" 기온 {t1h_temp}℃ "

        if val['REH'] :
            reh_temp = float(val['REH'])
            template += f"습도 {reh_temp}% "

        if val['VEC'] and val['WSD']:
            vec_temp = self.deg_to_dir(float(val['VEC']))
            wsd_temp = val['WSD']
            template += f"풍속 {vec_temp} 방향 {wsd_temp}m/s"

        return template

    def get_sky(self):
        key, val = self.get_info()

        template = ""

        if val['SKY']:
            sky_temp = self.sky_code[int(val['SKY'])]
            template += sky_temp

        return template



    def deg_to_dir(self, deg) :
        close_dir = ''
        min_abs = 360
        if deg not in self.deg_code.keys() :
            for key in self.deg_code.keys() :
                if abs(key - deg) < min_abs :
                    min_abs = abs(key - deg)
                    close_dir = self.deg_code[key]
        else :
            close_dir = self.deg_code[deg]
        return close_dir