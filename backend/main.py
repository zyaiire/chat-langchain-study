"""Main entrypoint for the app."""
import asyncio
from typing import Optional, Union
from uuid import UUID

import langsmith
from chain import ChatRequest, answer_chain
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware #NOTE - 允许跨域请求，方便前端调用
from langserve import add_routes
from langsmith import Client
from pydantic import BaseModel

client = Client() # 创建Langsmith的客户端

app = FastAPI() # 初始化FastAPi
#MY_WAY - 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 把项目的处理函数挂载到/chat路径 
#TODO - 为什么要挂载到/chat路径
add_routes(
    app,
    answer_chain,
    path="/chat",
    input_type=ChatRequest, #MY_WAY - 什么是定义前端的数据结构
                            #ANSWER - python可以用类定义参数
    config_keys=["metadata", "configurable", "tags"],
)

#MY_WAY - 用于定义前端把请求体转换为Python对象
class SendFeedbackBody(BaseModel): #NOTE - 请求体模型
    run_id: UUID # 本次对话的唯一标识
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


class UpdateFeedbackBody(BaseModel):
    feedback_id: UUID
    score: Union[float, int, bool, None] = None
    comment: Optional[str] = None


@app.patch("/feedback")
async def update_feedback(body: UpdateFeedbackBody):
    feedback_id = body.feedback_id
    if feedback_id is None:
        return {
            "result": "No feedback ID provided",
            "code": 400,
        }
    client.update_feedback(
        feedback_id,
        score=body.score,
        comment=body.comment,
    )
    return {"result": "patched feedback successfully", "code": 200}


# TODO: Update when async API is available
async def _arun(func, *args, **kwargs):
    return await asyncio.get_running_loop().run_in_executor(None, func, *args, **kwargs)


async def aget_trace_url(run_id: str) -> str:
    try:
        # Wait for run to be available
        for i in range(5):
            try:
                await _arun(client.read_run, run_id)
                break
            except Exception:
                await asyncio.sleep(1**i)

        # Check if run is shared and return appropriate URL
        try:
            if await _arun(client.run_is_shared, run_id):
                return await _arun(client.read_run_shared_link, run_id)
            return await _arun(client.share_run, run_id)
        except Exception as e:
            # If there's an error with sharing, return a fallback URL
            print(f"Error accessing LangSmith trace: {e}")
            return f"https://smith.langchain.com/o/default/projects/default/r/{run_id}"
    except Exception as e:
        # If all else fails, return a basic trace URL
        print(f"Error creating trace URL: {e}")
        return f"https://smith.langchain.com/trace/{run_id}"


class GetTraceBody(BaseModel):
    run_id: UUID

#SECTION - 溯源系统，langsmith的trace
@app.post("/get_trace")
async def get_trace(body: GetTraceBody):
    run_id = body.run_id
    if run_id is None:
        return {
            "result": "No LangSmith run ID provided",
            "code": 400,
        }
    return await aget_trace_url(str(run_id))

#SECTION - 程序启动
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
