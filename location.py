import requests
from dotenv import load_dotenv

load_dotenv()


KAKAO_REST_API_KEY = '046bf27b3e4417a888ee9c0f300e4f60'  # 카카오 API 키

class GetLocation:
    def __init__(self, data):
        self.data = data

    def convert_coordinates_to_address(self):
        """
        입력받은 위도, 경도를 도로명 주소 및 지번 주소로 변환하여 반환
        """
        result = {}  # 변환된 주소를 저장할 딕셔너리

        for user, info in self.data.items():
            lat, long = str(info["latitude"]), str(info["longitude"])
            url = f'https://dapi.kakao.com/v2/local/geo/coord2address.json?x={long}&y={lat}'
            header = {'Authorization': f'KakaoAK {KAKAO_REST_API_KEY}'}

            try:
                r = requests.get(url, headers=header)
                r.raise_for_status()  # HTTP 오류 발생 시 예외 발생

                response_data = r.json()
                if response_data["documents"]:
                    road_address = response_data["documents"][0].get("road_address", {}).get("address_name", "정보 없음")
                    bunji_address = response_data["documents"][0].get("address", {}).get("address_name", "정보 없음")
                else:
                    road_address, bunji_address = "주소 없음", "주소 없음"

                result[user] = {"road_address": road_address, "bunji_address": bunji_address}

            except requests.exceptions.RequestException as e:
                print(f"❌ {user}의 주소 변환 실패: {e}")
                result[user] = {"road_address": "변환 실패", "bunji_address": "변환 실패"}

        return result[list(result.keys())[0]]["road_address"].split(" ")[0], result[list(result.keys())[0]]["road_address"].split(" ")[1] # return 시도, 군구
