# 환경변수 로딩
from dotenv import load_dotenv
load_dotenv()

# 필요한 라이브러리 임포트
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
from spotipy.oauth2 import SpotifyClientCredentials
import os, json, ast, spotipy
import pandas as pd

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# 모델 초기화
model = init_chat_model("gpt-4o-mini", model_provider="openai")

def recommend_songs(recommended_songs, my_location, my_weather, target, pop_parameter, config, query, language):
    while len(recommended_songs) < target:
        # 프롬프트 생성: openai가 추천할 프롬프트 정의
        prompt_template = ChatPromptTemplate.from_messages(
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

        # 이전 사용자 메시지 기록 불러오기 기능 미구현
        from langchain_core.messages import AIMessage, SystemMessage, trim_messages
        trimmer = trim_messages(
            max_tokens=300,
            strategy="last",
            token_counter=model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )

        messages = []
        trimmer.invoke(messages)

        # 커스텀 상태 정의: 언어 입력
        class State(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]
            language: str

        # Define a new graph(스키마는 우리가 정의한 State)
        workflow = StateGraph(state_schema=State)

        # Define the function that calls the model. 인수는 우리가 정의한 State
        def call_model(state: State):
            trimmed_messages = trimmer.invoke(state["messages"])
            prompt = prompt_template.invoke(
                {"messages": trimmed_messages, "language": state["language"]}
            )
            response = model.invoke(prompt)
            return {"messages": response}

        # Define the (single) node in the graph
        workflow.add_edge(START, "model")
        workflow.add_node("model", call_model)

        # Add memory
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        input_messages = messages + [HumanMessage(query)]
        output = app.invoke(
            {"messages": input_messages, "language": language},
            config,
        )

        # 원활한 JSON 파일 변환을 위해 문자열 전처리 작업 선행
        music_dict = output["messages"][-1].content
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
                    recommended_songs[artist] = track

                if len(recommended_songs) == target:
                    break
            except:
                continue
    
    return recommended_songs

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

recommended_songs = recommend_songs(recommended_songs={}, my_location=f"{si} {do}", my_weather = f"{now_whea.get_sky()}", target=5, 
                                    pop_parameter=60, config={"configurable": {"thread_id": "abc678"}}, query="오늘은 기쁜 날이야.", language="Korean")



df = pd.DataFrame(recommended_songs.items(), columns=['artist', 'title'])
df.to_json("songs.json", force_ascii=False, indent=4)
