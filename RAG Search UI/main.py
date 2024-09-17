import os
from typing import List
import traceback
import uuid
import time
from langchain_community.vectorstores import Qdrant
from langchain.chains import (
    ConversationalRetrievalChain,
)
import openai
import tiktoken
import json

from langchain_community.chat_models import ChatOpenAI

from langchain.docstore.document import Document
from langchain.memory import ChatMessageHistory, ConversationBufferMemory
from langchain_openai import OpenAIEmbeddings  # Updated import for OpenAI embeddings

from qdrant_client import QdrantClient, AsyncQdrantClient
from quixstreams import Application
from quixstreams.models.serializers import (
    JSONSerializer,
    SerializationContext,
)
import logging
import chainlit as cl


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_apikey = os.environ['OPENAI_API_KEY']
collection = os.environ['collectionname']
#TEST COLLECTIONS: "quix-techdocs-no0_5b_1kchars" # "quix-techdocs-no0_5b"

openai_apikey = os.environ['OPENAI_API_KEY']

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(openai_api_key=openai_apikey, model="text-embedding-3-large")  # Updated to use OpenAI embeddings

outputtopicname = os.environ["output"]

@cl.on_chat_start
async def on_chat_start():
    client = QdrantClient(
                    url="https://20670375-f669-4a3f-a67e-dd533679b26d.us-east4-0.gcp.cloud.qdrant.io:6333",
                    api_key=os.environ['QDRANT_APIKEY'],
                    timeout=100,
                    grpc_port=6334,
                    prefer_grpc=True
                )
    # client = QdrantClient(path="./qdrant-db-buffer")
    
    aclient = AsyncQdrantClient(
                    url="https://20670375-f669-4a3f-a67e-dd533679b26d.us-east4-0.gcp.cloud.qdrant.io:6333",
                    api_key=os.environ['QDRANT_APIKEY'],
                    timeout=100,
                    grpc_port=6334,
                    prefer_grpc=True
                )
    # aclient = AsyncQdrantClient(path="./qdrant-db-buffer")
    


    vectorstore = Qdrant(
        async_client=aclient,
        client=client,
        collection_name=collection,
        embeddings=embeddings,
    )
    docs_retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 20})
    #docs_retriever = vectorstore.as_retriever()
    
    message_history = ChatMessageHistory()

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer",
        chat_memory=message_history,
        return_messages=True,
    )

    # Create a chain that uses the Qdrant vector store
    chain = ConversationalRetrievalChain.from_llm(
        ChatOpenAI(model_name="gpt-4", temperature=0.3, streaming=True),
        chain_type="stuff",
        retriever=docs_retriever,
        memory=memory,
        return_source_documents=True,
    )

    cl.user_session.set("chain", chain)


searchquery = ""
answer = ""
source_documents = []
text_elements = ""

# Example summarization pipeline using Hugging Face transformers
summarizer = pipeline("summarization")

encoding = tiktoken.encoding_for_model("gpt-4") 

# Function to modify documents
def modify_documents(documents):
    modified_documents = []
    for doc in documents:
        print(doc.metadata)
        # Example modification: Summarize the document content
        summarized_content = summarizer(doc.page_content, max_length=150, min_length=50, do_sample=False)
        # Create a new Document with the summarized content
        modified_doc = Document(page_content=summarized_content[0]['summary_text'], metadata=doc.metadata)
        modified_documents.append(modified_doc)
    return modified_documents

@cl.on_message
async def main(message: cl.Message):
        searchquery = message.content
        
        qdrant = QdrantClient(
            url="https://20670375-f669-4a3f-a67e-dd533679b26d.us-east4-0.gcp.cloud.qdrant.io:6333",
            api_key=os.environ['QDRANT_APIKEY'],
            grpc_port=6334,
            prefer_grpc=True,
            timeout=100
        )
        
        print("Search")

        hits = qdrant.search(
            collection_name=os.environ["collectionname"],
            query_vector=openai.embeddings.create(input=searchquery, model="text-embedding-3-large").data[0].embedding,
            limit=100
        )
        
        
        # for hit in hits:
        #     if "url" in hit.payload["metadata"] and hit.payload["metadata"]["url"].startswith("https://quix.io/docs/quix-streams"):
        #         hit.score = hit.score / 1.1
            
                
            

        hits = sorted(hits, key=lambda x: x.score, reverse=True)
        
        context_from_documents = "Context: \n"
        
        for hit in hits:
            logger.info(len(encoding.encode(context_from_documents + hit.payload["page_content"] + "\n" + "Question: {searchquery}") ))
            if len(encoding.encode(context_from_documents + hit.payload["page_content"] + "\n" + "Question: {searchquery}") ) > 2000:
                break
            
            print(hit.score)
            print(json.dumps(hit.payload["metadata"], indent=4))
            
            context_from_documents += hit.payload["page_content"] + "\n"
            
            
        
        # Retrieve documents from Qdrant
        #res = chain.retriever.get_relevant_documents(searchquery)  # Retrieve the documents
        
        # Modify the retrieved documents before passing them to the LLM
        #modified_documents = modify_documents(res)

        # Example: Combine documents' text into a single string and prepend it to the question
        
        #logger.info(context_from_documents)
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"Context: {context_from_documents} \nQuestion: \n" + searchquery,
                }
                ]
            )

        # Print the response
        logger.info(response)
        
        answer = response.choices[0].message.content
        
        await cl.Message(content=answer, elements=text_elements).send()
    #     source_documents = res["source_documents"]  # type: List[Document]
        
    #     for doc in source_documents:
    #         logger.info(f"Document: {doc.metadata}")

    #     # Log the source documents to see if any have None as page_content
    #     #logger.info(f"Source documents: {source_documents}")

    #     text_elements = []  # type: List[cl.Text]

    #     if source_documents:
    #         seen_urls = set()  # Set to track seen URLs
    #         text_elements = []  # Reset text_elements to ensure it's empty before adding new elements

    #         for source_idx, source_doc in enumerate(source_documents):
    #             source_url = source_doc.metadata.get('url', '#')
    #             if source_url not in seen_urls:  # Check if the URL has not been seen before
    #                 seen_urls.add(source_url)  # Mark this URL as seen

    #                 source_title = source_doc.metadata.get('title', f'Source_{source_idx + 1}')
    #                 # Remove " - Quix Docs" if it exists in the title
    #                 if source_title.endswith(" - Quix Docs"):
    #                     source_title = source_title[:-12]

    #                 markdown_link = f"* [{source_title}]({source_url})\n"  # Bullet point added
    #                 text_elements.append(cl.Text(content=markdown_link, name="markdown"))

    #         # Join with newline for bullet points
    #         source_links = ''.join([text_el.content for text_el in text_elements])

    #         if source_links:
    #             answer += f"\n\n**Sources:**\n{source_links}"
    #         else:
    #             answer += "\n\nNo sources found"

    #     await cl.Message(content=answer, elements=text_elements).send()
    # except Exception as e:
    #     logger.error(f"An error occurred: {e}")
    #     logger.error(traceback.format_exc())
    #     # Handle the error appropriately, possibly sending a message to the user

    #### START QUIX STUFF ######
    # app = Application.Quix()
    # # app = Application(broker_address='localhost:19092')
    # serializer = JSONSerializer()
    # topic = app.topic(name=outputtopicname, value_serializer=serializer)

    # source_documents_serializable = []
    
    # if source_documents:
    #     for doc in source_documents:
    #         source_documents_serializable.append( {
    #     "page_content": doc.page_content,
    #     "metadata": doc.metadata
    # })

    # load_dotenv("./quix_vars.env")
    # print(f"Producing to output topic: {outputtopicname}...\n\n")
    # idcounter = 0
    # with app.get_producer() as producer:
    #     idcounter = idcounter + 1
    #     doc_id = idcounter
    #     doc_key = f"A{'0'*(10-len(str(doc_id)))}{doc_id}"
    #     doc_uuid = str(uuid.uuid4())
    #     value = {
    #         "Timestamp": time.time_ns(),
    #         "query": searchquery,
    #         "answer": answer,
    #         "matching_docs": source_documents_serializable
    #         }

    #     print(f"Producing value: {value}...")
    #     # with current functionality, we need to manually serialize our data
    #     serialized = topic.serialize(
    #         key=doc_key,
    #         value=value,
    #         headers={**serializer.extra_headers, "uuid": doc_uuid},
    #     )

    #     producer.produce(
    #         topic=topic.name,
    #         headers=serialized.headers,
    #         key=serialized.key,
    #         value=serialized.value,
    #         )
