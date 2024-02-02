from llama_index.prompts import PromptTemplate
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
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank
from llama_index.indices.postprocessor import MetadataReplacementPostProcessor

from langchain_community.chat_models.huggingface import ChatHuggingFace
from langchain_community.llms import HuggingFaceTextGenInference
from llama_index.llms import LangChainLLM
from dataclasses import dataclass
# from llama_index.indices.document_summary import DocumentSummaryIndex


import asyncio
import json
from loguru import logger

f = open('ntc.json')
ntc_data = json.load(f)
f.close()


@dataclass
class NtcData:
    title: str
    tag:  list 
    link: str
    text: list 

visited_sites = []
def read_data(data, ntc_datas):
    for key, value in data.items():
        key = key
        value = value
    ntc_data = NtcData(
        title=value["title"], tag=value["tags"], link=key, text=value["text"])
    # ntc_data = NtcData(
    #     title="", tag=0, link=key, text=[])
    if ntc_data.link in visited_sites:
        return ntc_datas
    visited_sites.append(ntc_data.link)
    ntc_datas.append(ntc_data)
    children = value["children"]
    if children is None:
        return ntc_datas
    for child in children:
        read_data(data=child, ntc_datas=ntc_datas)
    return ntc_datas


ntc_datas = read_data(ntc_data, ntc_datas=[])
print(ntc_datas[0])

template = """
<s><INST>
Defn: An entity is a person(person), institute (institute), organisation (organisation), services(services),
packages(packages), information(information), organization(organization) ,,,event(event), award(award), or
theory(theory). Abstract communication concepts can be entities if they have a name associated with them.
If an entity does not fit the types above it is (misc). Dates, times, adjectives and verbs are not entities.

Example:
____________________________________________________
Q: Given the paragraph below, identify a list of possible entities and for each entry explain
why it either is or not an entity:

Paragraph: He attended the U.S Air Force Institute of Technology for a year, earning a bachelor's
degree in aeromechanics, and received his test pilot training at Edwards Air Force Base in
California before his assignment as a test pilot at Wright-Patterson Air Force Base in Ohio.

Answer:
1. U.S. Air Force Institute of Technology | True | as he attended this institue is likely a institute (institute)
2. bachelor's degree | False | as it is not a university, award or any other entity type
3. aeromechanics | True | as it is a discipline (discipline)
4. Edwards Air Force Base | True | as an Air Force Base is an organised unit (organisation)
5. California | True | as in this cas California refers to location (location)
6. Wright-Patterson Air Force Base | True | as an Air Force Base is an organisation (organisation)
7. Ohio | True | as it is a state (location)
____________________________________________________
Q: Given the paragraph below, identify a list of possible entities and for each entry explain
why it either is or not an entity:

Paragraph: {text}
</INST>
Answer:\n
"""

embed_model = LangchainEmbedding(
    HuggingFaceBgeEmbeddings(model_name="BAAI/bge-large-en-v1.5"))
client = weaviate.Client("http://localhost:8029")
# print(client)
vector_store = WeaviateVectorStore(
    weaviate_client=client, index_name="NTC_BOT_NO_ENTITY_TABLE_Metadata_tokens",
)
# required_exts = [".mmd"]
# docs = SimpleDirectoryReader(
#     input_dir="./wiseyak_file", required_exts=required_exts).load_data()

from llama_index.node_parser.text.utils import truncate_text

from llama_index.node_parser import TokenTextSplitter
sentence_splitter = TokenTextSplitter.from_defaults(chunk_size = 100, chunk_overlap = 20)

def split_by_token():
    from typing import List
    def split(text: str) -> List[str]:
        sentences = sentence_splitter.split_text(text)
        return sentences
    return split

node_parser = SentenceWindowNodeParser.from_defaults(
    sentence_splitter = split_by_token(),
    window_size=8,
    window_metadata_key="window",
    original_text_metadata_key="original_text",
)

# nodes = node_parser.get_nodes_from_documents(docs)


class ExtractEntity:
    def __init__(self, datas, node_parser):
        self.prompt_template = PromptTemplate(template)
        self.llm = LangChainLLM(llm=HuggingFaceTextGenInference(inference_server_url="http://192.168.88.10:8024",
                                                                max_new_tokens=2048,
                                                                top_k=10,
                                                                top_p=0.95,
                                                                typical_p=0.95,
                                                                temperature=0.01,
                                                                repetition_penalty=1.03,
                                                                streaming=True,),
                                )
        self.docs = self.format_data_in_docs(ntc_datas)
        self.node_parser = node_parser
        self.nodes = self.get_nodes_from_documents(self.docs, self.node_parser)
        # self.nodes_with_entity = self.extract_entity_from_nodes()
        self.nodes_with_entity = self.nodes
        self.bge_rerank_postprocessor = SentenceTransformerRerank(
            model="BAAI/bge-reranker-large",
            top_n=3
        )
        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store)
        self.service_context = ServiceContext.from_defaults(
            embed_model=embed_model, llm=self.llm)

    def build_index(self):
        self.index = VectorStoreIndex(
            nodes=self.nodes_with_entity, storage_context=self.storage_context, service_context=self.service_context, show_progress=True)
        # self.index = DocumentSummaryIndex(
        #     nodes=self.nodes_with_entity, storage_context=self.storage_context, service_context=self.service_context, show_progress=True)


    def format_data_in_docs(self, data):
        from llama_index import Document, VectorStoreIndex
        docs = []
        for ntc_data in ntc_datas:
            # metadata = {"title": ntc_data.title, "str_tag": str(ntc_data.tag),
            #             "link": ntc_data.link, "text": str(ntc_data.text)}
            metadata = {"title": ntc_data.title, "str_tag": str(ntc_data.tag),
                        "link": ntc_data.link,}
            docs.append(Document(text=" ".join(
                ntc_data.text), 
                metadata=metadata, excluded_embed_metadata_keys=list(metadata.keys()) ,excluded_llm_metadata_keys=list(metadata.keys())))
        return docs

    def get_nodes_from_documents(self, docs, node_parser):
        nodes = node_parser.get_nodes_from_documents(docs)
        return nodes

    def parse_entity(self, response):
        list_of_entities = response.text.split("\n")
        entities = []
        for entity in list_of_entities:
            entity_value = entity.split("|")
            try:
                if entity_value[1].replace(" ", "") == "True":
                    value = entity_value[0].split(" ", 1)[1]
                    if len(value) < 60:
                        entities.append(value)
            except:
                continue
        return entities

    async def extract_entity_from_nodes(self):
        self.nodes_with_entity = []
        word_count = []
        max_word_length = 1050
        for i, node in enumerate(self.nodes):
            entities = []
            words = node.metadata["window"].split(" ")
            if len(words) > max_word_length:
                count = 0
                while len(words) > max_word_length:
                    if count > 3:
                        break
                    texts = " ".join(words[:max_word_length])
                    response = await self.llm.acomplete(
                        self.prompt_template.format(text=texts))
                    logger.debug(f"Working on Node: {i+1}")
                    entities.extend(self.parse_entity(response))
                    words = words[max_word_length:]
                    count += 1
                texts = " ".join(words[:max_word_length])
                response = await self.llm.acomplete(
                    self.prompt_template.format(text=texts))
                logger.debug(f"Working on Node: {i+1}")
                entities.extend(self.parse_entity(response))
            else:
                response = await self.llm.acomplete(
                    self.prompt_template.format(text=node.metadata["window"]))
                logger.debug(f"Working on Node: {i+1}")
                entities = self.parse_entity(response)
            node.metadata["entity"] = entities
            self.nodes_with_entity.append(node)
        return self.nodes_with_entity

    def query_anything(self, query):
        query_engine = self.index.as_query_engine(similarity_top_k=8, node_postprocessors=[self.bge_rerank_postprocessor, MetadataReplacementPostProcessor(
            target_metadata_key="window")])  # node_postprocessors=[self.bge_rerank_postprocessor]
        # Make the query asynchronously
        streaming_response = query_engine.query(query)
        return streaming_response


if __name__ == "__main__":
    ee = ExtractEntity(datas=ntc_datas, node_parser=node_parser)
    # _ = asyncio.run(ee.extract_entity_from_nodes())
    ee.build_index()
    response = ee.query_anything("What are fixed lines?")
    print(response)
    print(response.source_nodes[0].metadata)