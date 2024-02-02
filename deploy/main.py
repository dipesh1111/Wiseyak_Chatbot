from typing import Union
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from chat import ConversationalAI
from pydantic import BaseModel
from fastapi.responses import UJSONResponse

model = ConversationalAI()
app = FastAPI()

class Query(BaseModel):
    text: str

@app.post("/text", response_class=UJSONResponse)
async def gen(question: Query, request: Request):
    print("Question:", question.text)  # Access the query parameter using question.query
    
    try:
        if question.text:
            text = model._response(question.text)
            return {"model_response": text}
        else:
            return  Response(content="Please, record your voice again.", media_type="application/json")
    except Exception as e:
        error_message = {"Error While Generating Response, Please Try Again!!!": str(e)}
        return Response(content=error_message, media_type="application/json")
    

# @app.post("/text")
# async def main(question: Query, request: Request):
#     print("Question:", question.text)  # Access the query parameter using question.query
    
#     try:
#         if question.text:
#             return Response(model._response_query(question.text), media_type='text/event-stream')
#         else:
#             return  Response(content="Please, record your voice again.", media_type="application/json")
#     except Exception as e:
#         error_message = {"Error While Generating Response, Please Try Again!!!": str(e)}
#         return Response(content=error_message, media_type="application/json")
