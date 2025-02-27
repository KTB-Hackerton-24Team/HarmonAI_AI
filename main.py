from fastapi import FastAPI
from typing import Union
from typing import List
from pydantic import BaseModel
import pandas as pd

from location import GetLocation
from wheather import Wheather
from recommend_songs import Recommend_songs


app = FastAPI()

class RequestData(BaseModel):
    latitude: float
    longitude: float
    message: str
    pop: int
    

    class Config:
        orm_mode = True

class ResponseData(BaseModel):
    title: str
    artist: str

    class Config:
        orm_mode = True

# Song artist Class 생성하기
# 테스트 데이터

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/test", response_model = RequestData)
async def response_process(data: RequestData):
    print(data)

    return data

@app.post("/api/info/current", response_model = List[ResponseData])
async def response_process(data: RequestData):
    
    loca = GetLocation(data).convert_coordinates_to_address()
    now_whea = Wheather(f"{loca.split(sep = " ")[1]}", f"{loca.split(sep = " ")[2]}")

    playlist = Recommend_songs(max(pop, 20))
    my_musics = playlist.recommend(f"{loca}", f"{now_whea.get_sky()}", 5, 
    {"configurable": {"thread_id": "abc678"}}, "오늘은 기쁜 날이야.", "Korean")

    df = pd.DataFrame(my_musics.items(), columns=['artist', 'title'])
    songs_list = df.to_dict(orient = 'records')

    return songs_list
