### IMPORT THE STUFF
from quix_docs_parser import quix_docs_extractor
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import logging
import uuid
import pickle
from dotenv import load_dotenv

import time
import os
from bs4 import BeautifulSoup, SoupStrainer
from langchain_community.document_loaders import SitemapLoader
from quixstreams import Application
from quixstreams.models.serializers import (
    JSONSerializer,
    SerializationContext,
)

def save_docs_to_file(docs, file_dir, file_name):
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    file_path= os.path.join(file_dir, file_name)
    with open(file_path, 'wb') as f:
        pickle.dump(docs, f)

def load_docs_from_file(file_dir, file_name):
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    file_path= os.path.join(file_dir,file_name)
    with open(file_path, 'rb') as f:
        return pickle.load(f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
outputtopicname = os.environ["output"]
use_local_bool = os.environ['use_local_crawl_pickle'] == "True"

textchunksize = int(os.environ['textchunksize'])
textoverlapsize = int(os.environ['textoverlapsize'])

### USING WEB CRAWLER
# Inspired by: https://github.com/langchain-ai/chat-langchain/blob/master/ingest.py

def metadata_extractor(meta: dict, soup: BeautifulSoup) -> dict:
    title = soup.find("title")
    description = soup.find("meta", attrs={"name": "description"})
    html = soup.find("html")
    return {
        "source": meta["loc"],
        "title": title.get_text() if title else "",
        "description": description.get("content", "") if description else "",
        "language": html.get("lang", "") if html else "",
        **meta,
    }

def load_quix_docs():
    return SitemapLoader(
        "https://quix.io/docs/sitemap.xml",
        filter_urls=[
            r"https://quix.io/docs/(?!v0-5-stable/).*"
        ],
        parsing_function=quix_docs_extractor,
        default_parser="lxml",
        bs_kwargs={
            # COMMENTING OUT TO GET FULL HTML
            # "parse_only": SoupStrainer(
            #    name="article", class_=re.compile("md-content__inner")
            #),
        },
        meta_function=metadata_extractor,
    ).load()

def simple_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\n\n+", "\n\n", soup.text).strip()

def ingest_docs(use_local=False, local_dir="state", local_file='quixdocs.pickle'):
    if use_local:
        # Load the docs from the local pickle file
        docs_from_documentation = load_docs_from_file(local_dir, local_file)
        logger.info(f"Loaded {len(docs_from_documentation)} docs from local file")
    else:
        # Crawl the docs and save to the local pickle file
        docs_from_documentation = load_quix_docs()
        logger.info(f"Loaded {len(docs_from_documentation)} docs from documentation")
        save_docs_to_file(docs_from_documentation, local_dir, local_file)
        logger.info(f"Saved docs to {local_dir}/{local_file}")
    
    #docs_from_documentation = load_quix_docs_local()
    logger.info("Logging first 5 docs..")
    for d in range(min(5, len(docs_from_documentation))):
        doc = docs_from_documentation[d]
        logger.info(f"Doc {d} is:\n page_content='{doc.page_content}' metadata={doc.metadata} |")

    # Check if any documents are empty and log a warning if so
    empty_docs = [doc for doc in docs_from_documentation if not doc.page_content.strip()]
    if empty_docs:
        logger.warning(f"Found {len(empty_docs)} empty documents. They will not be split.")


    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=textchunksize,
        chunk_overlap=textoverlapsize)
    docs_transformed = text_splitter.split_documents(
        docs_from_documentation
    )
    logger.info(f"Docs after split {len(docs_transformed)}")
    if docs_transformed:
        for d in range(min(5, len(docs_transformed))):
            logger.info(f"SplitDoc {d} is:\n {docs_transformed[d]} |")
    else:
        logger.error("No documents were split. Please check the input documents and the text splitter configuration.")

    return docs_transformed

quixdocs = ingest_docs(use_local=use_local_bool)

#### START QUIX STUFF ######
app = Application.Quix()
#app = Application(broker_address='localhost:19092')
serializer = JSONSerializer()
topic = app.topic(name=outputtopicname, value_serializer=serializer)

source_documents_serializable = [
{
"page_content": doc.page_content,
"metadata": doc.metadata
}
for doc in source_documents
]

# load_dotenv("./quix_vars.env")
print(f"Producing to output topic: {outputtopicname}...\n\n")
serialize = JSONSerializer()
idcounter = 0
with app.get_producer() as producer:
    for doc in quixdocs:
        doctext = re.sub(r'\n+', '\n', doc.page_content)
        doctext = re.sub(r' +', ' ', doctext)

        doc_id = idcounter
        doc_key = f"A{'0'*(10-len(str(doc_id)))}{doc_id}"
        doc_uuid = str(uuid.uuid4())
        headers = {**serialize.extra_headers, "uuid": doc_uuid}

        value = {
            "Timestamp": time.time_ns(),
            "doc_id": doc_id,
            "doc_uuid": doc_uuid,
            "doc_title": doc.metadata['title'],
            "doc_content": doctext,
            "doc_source": doc.metadata['source'],
        }

        print(f"Producing value: {value}")
        idcounter = idcounter + 1
        producer.produce(
            topic=outputtopicname,
            headers=headers,  # a dict is also allowed here
            key=doc_key,
            value=serialize(
                value=value, ctx=SerializationContext(topic=outputtopicname, headers=headers)
            ),  # needs to be a string
        )

print("ingested quix docs")