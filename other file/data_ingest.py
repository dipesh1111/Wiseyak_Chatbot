from llama_index import VectorStoreIndex, SimpleDirectoryReader
from llama_index.vector_stores import WeaviateVectorStore
import weaviate
from llama_index.node_parser import (
    SentenceWindowNodeParser,
)
from llama_index import (
    GPTVectorStoreIndex,
    ServiceContext,
    StorageContext
)
from llama_index.embeddings import LangchainEmbedding
from langchain.embeddings.huggingface import (
    HuggingFaceBgeEmbeddings,
)

embed_model = LangchainEmbedding(HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-en-v1.5"))
client = weaviate.Client("http://localhost:8080")
vector_store = WeaviateVectorStore(
    weaviate_client=client, index_name="LlamaIndex"
)
required_exts = [".mmd"]
docs = SimpleDirectoryReader(input_dir="./wiseyak_data", required_exts=required_exts).load_data()
node_parser = SentenceWindowNodeParser.from_defaults(
    window_size=10,
    window_metadata_key="window",
    original_text_metadata_key="original_text",
)

nodes = node_parser.get_nodes_from_documents(docs)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
service_context = ServiceContext.from_defaults(embed_model=embed_model,llm=None)
index = VectorStoreIndex(nodes=nodes,storage_context=storage_context,service_context=service_context,show_progress=True)