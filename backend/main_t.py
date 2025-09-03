from fastapi import FastAPI

app = FastAPI()

@app.get("/") # 当访问到根目录的时候，用以确定服务是否可用
def ping():
    return {"ok":True} 

from fastapi.middleware.cors import CORSMiddleware
# 允许跨域请求，方便前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 开发期先全开，发布时收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from langserve import add_routes
from chain import ChatRequest, answer_chain  # 你的链与输入模型
#SECTION - Step3 通过LangServe把你的链“挂成”/chat
# 把链暴露为 /chat 前缀
add_routes(
    app,
    answer_chain,
    path="/chat",
    input_type=ChatRequest,
    config_keys=["metadata", "configurable", "tags"],
)

#SECTION - Step4 用户反馈
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel
from langsmith import Client

client = Client()

class SendFeedbackBody(BaseModel):
    run_id: UUID
    key: str = "user_score"
    score: Union[float, int, bool, None] = None
    feedback_id: Optional[UUID] = None
    comment: Optional[str] = None

@app.post("/feedback")
async def send_feedback(body: SendFeedbackBody):
    client.create_feedback(
        body.run_id,
        body.key,
        score=body.score,
        comment=body.comment,
        feedback_id=body.feedback_id,
    )
    return {"result": "posted feedback successfully", "code": 200}

#SECTION - Sept5 朔源链接

import asyncio

async def _arun(func, *args, **kwargs):
    return await asyncio.get_running_loop().run_in_executor(None, func, *args, **kwargs)

class GetTraceBody(BaseModel):
    run_id: UUID

@app.post("/get_trace")
async def get_trace(body: GetTraceBody): #NOTE - asyn代表异步函数，网络请求，数据库查询，调用外部API时适合
    run_id = str(body.run_id)
    # 1) 等 run 可读
    for i in range(5):
        try:
            await _arun(client.read_run, run_id)
            break
        except Exception:
            await asyncio.sleep(1**i) # sleep会阻塞服务
    # 2) 已分享则读分享链接，否则分享之
    try:
        if await _arun(client.run_is_shared, run_id):
            return await _arun(client.read_run_shared_link, run_id)
        return await _arun(client.share_run, run_id)
    except Exception:
        # 兜底：返回一个可推断的 URL
        return f"https://smith.langchain.com/o/default/projects/default/r/{run_id}"
    
#SECTION - Sept6 启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # 或命令行：uvicorn main:app --reload --port 8080