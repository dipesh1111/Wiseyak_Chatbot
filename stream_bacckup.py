from llama_index import (
    GPTVectorStoreIndex,
    ServiceContext
)
import re
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank
import gradio as gr
from llama_index.embeddings import LangchainEmbedding
import nltk
from langchain.embeddings.huggingface import (
    HuggingFaceBgeEmbeddings,
)
from llama_index.indices.postprocessor import MetadataReplacementPostProcessor
from llama_index.memory import ChatMemoryBuffer
import nltk
import pinecone
from llama_index.vector_stores import PineconeVectorStore
from llama_index.llms import HuggingFaceLLM
from llama_index.prompts import PromptTemplate
from prompt import MISTRAL_SYSTEM_PROMPT, CONTEXT_TEMPLATE, MISTRAL_QA_PROMPT

cohere_key = "ChwtBzyaCRjj0rdDmb559B2bt5y32yxH7rnXCu3C"
hf_auth = "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"
pinecone_api = "4d7c6d22-ef91-4819-8905-0962b03c0763"
pinecone_env = "gcp-starter"
nltk.download('punkt')

class ConversationalAI:
    def __init__(self):
        self.embed_model = LangchainEmbedding(HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-en-v1.5",cache_folder='./all_model/bge-large')) #Wiseyak-accountgpt/finetuned_bge1.5
        self.llm = HuggingFaceLLM(
            context_window=4096,
            max_new_tokens=512,
            generate_kwargs={"temperature": 0.01, "do_sample": True, "repetition_penalty":1.1,"top_p":0.95,"top_k":40},
            tokenizer_name="TheBloke/Mistral-7B-OpenOrca-GPTQ", #TheBloke/Mistral-7B-OpenOrca-GPTQ
            model_name="TheBloke/Mistral-7B-OpenOrca-GPTQ",
            device_map="cuda:0",
            tokenizer_kwargs={"max_length": 4096},
            model_kwargs = {'revision':'gptq-8bit-128g-actorder_True','cache_dir':'./all_model/mistral-openorca'},
        )

        # Initialize ServiceContext
        self.service_context = ServiceContext.from_defaults(
            embed_model=self.embed_model,
            llm=self.llm

        )
        self.bge_rerank_postprocessor = SentenceTransformerRerank(
        model="./all_model/rerank/bge-reranker-large", 
        top_n=3
        )

        #Initialize Memory
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=3000)

        # Initialize Pinecone Vectorstore
        pinecone.init(api_key=pinecone_api, environment=pinecone_env)
        pinecone_index = pinecone.Index("wiseyak-chatbot")
        self.vector_store = PineconeVectorStore(pinecone_index=pinecone_index, add_sparse_vector=True)
        self.index = GPTVectorStoreIndex.from_vector_store(self.vector_store, service_context=self.service_context)

        # Initializing prompts
        self.chat_prompt = MISTRAL_SYSTEM_PROMPT
        self.qa_prompt = PromptTemplate(MISTRAL_QA_PROMPT)

        # For Postprocessing
        self.pattern = re.compile(r'<\|assistant\|>|<\/s><|im_end|>')
        self.pattern1 = re.compile(r"<\|im_end\|>")

    def _response_query(self, query):
        query_engine = self.index.as_query_engine(text_qa_template=self.qa_prompt, similarity_top_k=8, node_postprocessors=[self.bge_rerank_postprocessor,MetadataReplacementPostProcessor(target_metadata_key="window")], streaming=True)  # node_postprocessors=[self.bge_rerank_postprocessor]

        # Make the query asynchronously
        streaming_response = query_engine.query(query)

        for i in range(len(streaming_response.source_nodes)):
            print("NODE :", streaming_response.source_nodes[i])
        
        for text in streaming_response.response_gen:
            resp = self.pattern1.sub("", text)
            yield resp

    def _response(self, query,history):
        chat_engine = self.index.as_chat_engine(
                                                chat_mode="context", 
                                                memory=self.memory,
                                                system_prompt= self.chat_prompt,
                                                context_template= CONTEXT_TEMPLATE,
                                                similarity_top_k=8,
                                                node_postprocessors=[self.bge_rerank_postprocessor, MetadataReplacementPostProcessor(target_metadata_key="window")],
                                                verbose=True)
        streaming_response = chat_engine.chat(query)
        for i in range(len(streaming_response.source_nodes)):
            print("NODE No", i)
            print("-------------------------------------------")
            print("NODE :", streaming_response.source_nodes[i])

        if streaming_response.source_nodes[0].score >= 0.00:
            resp = self.pattern.sub('', streaming_response.response)
            print("RESPONSE: ", resp)
            return resp
        else:
            return "I don't have much reference to your question. Please rephrase your question related to wiseyak."

    def start_interface(self):
        demo = gr.Interface(
            fn=self._response,
            inputs="text",
            outputs = [gr.Textbox(label="RESPONSE")],
        ).queue().launch(debug=True, share=True)
        
    def stream_gradio(self):
        gr.ChatInterface(self._response_query).queue().launch(share=True) 

# if __name__=="__main__":
#     app=ConversationalAI()
#     app.stream_gradio()
