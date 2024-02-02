from llama_index import (
    GPTVectorStoreIndex,
    ServiceContext,
)
from llama_index.postprocessor import SentenceTransformerRerank
from llama_index.embeddings import LangchainEmbedding
from langchain.embeddings.huggingface import (
    HuggingFaceBgeEmbeddings,
)
from llama_index.vector_stores import WeaviateVectorStore
from llama_index.postprocessor import MetadataReplacementPostProcessor
import weaviate
from llama_index.prompts.base import PromptTemplate
from prompt import MISTRAL_V2_CHAT
from langchain_community.llms import HuggingFaceTextGenInference
from llama_index.llms import LangChainLLM
from llama_index.memory import ChatMemoryBuffer
 
import re
from llama_index import (
    ServiceContext,
    set_global_handler,
)
 
from typing import List
from llama_index.bridge.langchain import (
    HumanMessage,
)
from llama_index.bridge.langchain import BaseMessage

from langchain_community.chat_models.huggingface import ChatHuggingFace
from huggingface_hub.commands.user import login

 
token = "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"
if login(token=token):
    print("Login success")
 
client = weaviate.Client("http://192.168.88.10:8080")
vector_store = WeaviateVectorStore(
    weaviate_client=client, index_name="LlamaIndex"
)
 
 
class CustomChatHuggingFace(ChatHuggingFace):
    def _to_chat_prompt(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Convert a list of messages into a prompt format expected by wrapped LLM."""
        if not messages:
            raise ValueError("at least one HumanMessage must be provided")
 
        if not isinstance(messages[-1], HumanMessage):
            raise ValueError("last message must be a HumanMessage")
 
        messages_dicts = [self._to_chatml_format(m) for m in messages]
        system_str = "<s>[INST] "+ messages_dicts.pop(0)['content'] + " </INST>"
        chat_str = self.tokenizer.apply_chat_template(
            messages_dicts, tokenize=False, add_generation_prompt=True
        )
        return system_str + chat_str
 
class ConversationalAI:
    def __init__(self):
        self.embed_model = LangchainEmbedding(HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-en-v1.5",cache_folder='./all_model/bge-large')) 
        self.llm = LangChainLLM(llm = CustomChatHuggingFace( llm =
                HuggingFaceTextGenInference(inference_server_url="http://192.168.88.10:8024",
                max_new_tokens=2048,
                top_k=10,
                top_p=0.95,
                typical_p=0.95,
                temperature=0.01,
                repetition_penalty=1.03,
                streaming=True,),
                model_id ="TheBloke/Mistral-7B-Instruct-v0.2-AWQ"
            ))

        # Initialize ServiceContext
        self.service_context = ServiceContext.from_defaults(
            embed_model=self.embed_model,
            llm=self.llm
 
        )
        self.bge_rerank_postprocessor = SentenceTransformerRerank(
        model="./all_model/rerank/bge-reranker-large",
        top_n=3
        )
 
        # Initialize Memory
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=4000)
 
        # Initialize vectorstore
        self.index = GPTVectorStoreIndex.from_vector_store(vector_store=vector_store, service_context=self.service_context)
 
        self.chat_prompt = PromptTemplate(MISTRAL_V2_CHAT)
        self.pattern = re.compile(r"<\|im_end\|>")
 
    def get_memory_token_count(self):
        chat_history = self.memory.get_all()
        msg_str = " ".join(str(m.content) for m in chat_history)
        return len(self.memory.tokenizer_fn(msg_str))
    
    def prune_memory(self, chat_limit):
        chat_history = self.memory.get_all()
        if len(chat_history) > chat_limit:
            self.memory.chat_store.set_messages(self.memory.chat_store_key, chat_history[2:])

 
 
    def _response(self, query):
        chat_engine = self.index.as_chat_engine(
                                                chat_mode="context",
                                                memory=self.memory,
                                                system_prompt= MISTRAL_V2_CHAT,
                                                # context_template= self.context_prompt,
                                                similarity_top_k=8,
                                                node_postprocessors=[self.bge_rerank_postprocessor, MetadataReplacementPostProcessor(target_metadata_key="window")],
                                                verbose=True)
        streaming_response = chat_engine.chat(query)
        for i in range(len(streaming_response.source_nodes)):
            print("NODE No", i)
            print("-------------------------------------------")
            print("NODE :", streaming_response.source_nodes[i])
 
        self.prune_memory(chat_limit = 4)
        print("Response :", streaming_response.response)
        return streaming_response.response