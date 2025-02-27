#구글맵 api 로드
import googlemaps
from dotenv import load_dotenv
import os


class GetLocation:
  def __init__(self, data):
    load_dotenv()
    self.data = data
    self.google_map_key = "AIzaSyBImt7oXDGSTfBfh2hlJZqPDB7Q-ZilYBk"

  def convert_coordinates_to_address(self):
    """
    입력받은 위도, 경도를 도로명 주소 및 지번 주소로 변환하여 반환
    """
    data_dict = self.data.dict()  # Pydantic 모델을 dict로 변환
    lat = float(data_dict["latitude"])
    long = float(data_dict["longitude"])
    self.gmaps = googlemaps.Client(key=self.google_map_key)
    result = self.gmaps.reverse_geocode((lat, long), language="ko")  # language="ko" 추가!
    return result[0]['formatted_address']