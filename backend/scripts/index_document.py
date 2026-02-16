import os 
import logging 
import glob
from dotenv import load_dotenv

load_dotenv(override=True)
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch

logger = logging.getLogger("brand-compliance-rules")
logging.basicConfig(level=logging.INFO , format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def index_docs():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir , "../../backend/data")
    # pdf_files = glob.glob(os.path.join(doc_dir , "*.pdf"))
    logger.info("="*60)
    logger.info("Environment Configuration Check :")
    
    

    logger.info("=" * 60)
    logger.info("AWS Environment Configuration Check:")

    logger.info(f"AWS_ACCESS_KEY_ID : {os.getenv('AWS_STORAGE_CONNECTION_STRING')}")
    logger.info(f"AWS_OPENAI_KEY : {os.getenv('AWS_OPEN_AI_KEY')}")
    logger.info(f"AWS_REGION : {os.getenv('REGION')}")

    logger.info(f"Model ID : {os.getenv('AWS_OPENAI_MODEL')}")
    logger.info(f"Embedding Model : {os.getenv('AWS_OPENAI_EMBEDDING_DEPLOYMENT')}")

    logger.info(f"OpenSearch Endpoint : {os.getenv('AWS_SEARCH_ENDPOINT')}")
    logger.info(f"OpenSearch Index : {os.getenv('AWS_SEARCH_INDEX_NAME')}")

    logger.info("=" * 60)
    

    # required variables

    required_vars = [
    "AWS_STORAGE_CONNECTION_STRING",
    "AWS_OPEN_AI_KEY",
    "REGION",
    "AWS_OPENAI_MODEL",
    "AWS_OPENAI_EMBEDDING_DEPLOYMENT",
    "AWS_SEARCH_ENDPOINT",
    "AWS_SEARCH_API_KEY",
    "AWS_SEARCH_INDEX_NAME"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file and ensure all variables are set")
        return

    # initialize the embedding model
    try:
        logger.info("Initializing the embedding model")
        embeddings = BedrockEmbeddings(

            model_id=os.getenv("AWS_OPENAI_EMBEDDING_DEPLOYMENT"),
            region_name=os.getenv("REGION")
        )
        logger.info("Embedding model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize embedding model: {e}")
        return

    # initialize the vector store
    try:
        logger.info("Initializing the vector store")
        vector_store = OpenSearchVectorSearch(
            opensearch_url=os.getenv("AWS_SEARCH_ENDPOINT"),
            index_name=os.getenv("AWS_SEARCH_INDEX_NAME"),
            embedding_function=embeddings.embed_query,
        )
        logger.info("Vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        return

    # load the documents
    pdf_files = glob.glob(os.path.join(data_folder , "*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {data_folder}")
    logger.info(f"Found {len(pdf_files)} PDF files: {[os.path.basename(pdf_file) for pdf_file in pdf_files]}")
    
    splits = []
    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing {pdf_file}")
            loader = PyPDFLoader(pdf_file)
            raw_docs = loader.load()
            # split the documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            )
            chunks = text_splitter.split_documents(raw_docs)
            splits.extend(chunks)
            logger.info(f"Split {len(chunks)} chunks from {pdf_file}")
        except Exception as e:
            logger.error(f"Failed to process {pdf_file}: {e}")
            continue

        # addition to the DB
        if splits:
            logger.info(f"Uploading {len(splits)} chunks to OpenSearch")
            try:
                vector_store.add_documents(splits)
                logger.info("="*60)
                logger.info(f"Successfully uploaded {len(splits)} chunks to OpenSearch")
                logger.info("="*60)
                # splits = []
            except Exception as e:
                logger.error(f"Failed to upload {len(splits)} chunks to OpenSearch: {e}")
                continue
        else:
            logger.warning("No Documents were processed")

if __name__ == "__main__":
    index_docs()
