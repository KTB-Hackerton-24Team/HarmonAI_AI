# 환경변수 로딩
from dotenv import load_dotenv
load_dotenv()

# 필요한 라이브러리 임포트
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Sequence
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
from spotipy.oauth2 import SpotifyClientCredentials
import os, json, ast, spotipy
import pandas as pd

# Spotipy 아이디, 비밀 키 로딩
client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# 모델 초기화
model = init_chat_model("gpt-4o-mini", model_provider="openai")

class recommend_songs:
    def __init__(self):
        self.recommended_songs = {}

    def recommend(self, my_location, my_weather, target, pop_parameter, config, query, language):
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "사용자가 기분을 입력하면 감성을 분석해서 해당 감성에 맞는 장르의 노래를 추천해줘. "
                    f"현재 장소는 {my_location}이고 오늘의 날씨는 {my_weather}이야. "
                    f"오늘의 장소와 날씨, 그리고 사용자의 감성을 분석해서 어울리는 노래 {target * 2}개를 추천해줘. "
                    "사용자의 언어를 고려하여 해당 언어가 속한 국가의 노래 위주로 70%, "
                    "이외 글로벌한 국가에 대해 30% 비중으로 노래를 추천해줘. "
                    "출력 형식은 반드시 JSON이어야 하며, 자연어는 출력하지 마. "
                    "아티스트나 노래 제목에 쌍따옴표가 있는 경우 작은따옴표로 변환해서 출력해줘."
                    "출력 형식 예시는 다음과 같아: "
                    '{{ "iu": "좋은 날", "blackpink": "How You Like That" , "Justin Timberlake": "Can\'t Stop the Feeling!"}}. '
                    "반드시 Spotify에서 검색 가능한 공식 아티스트명과 곡 제목을 사용해줘."
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
            )
        class State(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]
            language: str

        class CustomState(State):
            messages: list
            language: str

        while len(self.recommended_songs) < target:
            # 모델 호출 함수 정의
            def call_model(state: CustomState):
                prompt = self.prompt_template.invoke(
                    {"messages": state["messages"], "language": state["language"]}
                )
                response = model.invoke(prompt)
                return {"messages": response}

            # 그래프 생성 및 노드 연결
            workflow = StateGraph(state_schema=CustomState)
            workflow.add_edge(START, "model")
            workflow.add_node("model", call_model)

            # 애플리케이션 실행
            app = workflow.compile()

            # 입력 메시지 설정
            input_messages = [HumanMessage(query)]
            output = app.invoke(
                {"messages": input_messages, "language": language}
            )

            # 원활한 JSON 파일 변환을 위해 문자열 전처리 작업 선행
            music_dict = output["messages"].content
            music_dict = music_dict.replace("'", "")
            if not music_dict:
                continue
            try:
                music_dict = json.loads(music_dict)
            except:
                print('오류가 발생했습니다. 애플리케이션을 재실행합니다.')
                continue

            # 미리 설정한 Popularity Parameter에 따라 트랙 조절
            for key, value in music_dict.items():
                artist, track = key, value
                query = f"{artist} {track}"  # 아티스트 + 곡 제목 검색
                results = sp.search(q=query, type="track", limit=1)

                try:
                    track_popularity = results["tracks"]["items"][0]["popularity"]
                    if track_popularity <= pop_parameter:
                        self.recommended_songs[artist] = track

                    if len(self.recommended_songs) == target:
                        break
                except:
                    continue
        
        return self.recommended_songs

# 테스트 데이터
user_location_data = {
    "user_1": {"latitude": 37.5665, "longitude": 126.9780},
    "user_2": {"latitude": 35.1796, "longitude": 129.0756}  # 부산 예시
}

# 지역
from location import GetLocation
si, do = GetLocation(user_location_data).convert_coordinates_to_address()

# 날씨
from wheather import wheather
now_whea = wheather(f"{si}", f"{do}")

playlist = recommend_songs()
my_musics = playlist.recommend(f"{si} {do}", f"{now_whea.get_sky()}", 5, 60, 
 {"configurable": {"thread_id": "abc678"}}, "오늘은 기쁜 날이야.", "Korean")

df = pd.DataFrame(my_musics.items(), columns=['artist', 'title'])
df.to_json("songs.json", force_ascii=False, indent=4)
