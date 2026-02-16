import json 
import os 
import logging 
import re 
import json
import os
import logging
import re
from typing import Dict , Any , List

from langchain_aws import ChatBedrock
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage , SystemMessage

from src.utils.device import get_device
from backend.src.graph.state import VideoAuditState , complianceIssue

from backend.src.services.video_index import VideoIndexerServices

logger = logging.getLogger("brand-compliance-rules")
logging.basicConfig(level=logging.INFO)

# INDEXER

def index_video_node( state: VideoAuditState) -> Dict[str , Any]:
    """
    download -> stores blob storage -> extract insights
    """
    video_url = state.get("video_url")
    video_id = state.get("video_id")

    logger.info(f" processing video : {video_url}")

    local_filename = "temp_audit_video.mp4"
    try:
        vi_service = VideoIndexerServices()
        # download part
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(video_url , output_path=local_filename)

        else:
            raise Exception("Please provide a valid youtube URL")
        # upload part

        import boto3
        s3 = boto3.client("s3")
        s3.upload_file(local_path, "orchestra00998", f"videos/{video_id}.mp4")

        rekognition = boto3.client("rekognition", region_name="eu-north-1")

        response = rekognition.start_label_detection(
            Video={
                "S3Object": {
                    "Bucket": "orchestra00998",
                    "Name": f"videos/{video_id}.mp4"
                }
            }
        )

        job_id = response["JobId"]

        logger.info(f"Video uploaded and Rekognition Job ID: {job_id}")

        # azure_video_id = vi_service.upload_to_azure_video_indexer(local_path , video_id)
        # logger.info(f"Video uploaded to Azure Video Indexer with ID: {azure_video_id}")


        # cleaning

        if os.path.exists(local_path):
            os.remove(local_path)

        raw_insights = vi_service.get_insights(job_id)

        # extract
        clean_data = vi_service.extract_data(raw_insights)
        logger.info(f"-----[NODE : Indexer] Extraction Completed-------")
        return clean_data

    except Exception as e:
        logger.error(f"Error in index_video_node: {str(e)}")
        
        return {
            "erros": [str(e)],
            "final_status": "failed",
            "final_message": "Failed to index video",
            "transcript": "",
            "ocr_text": [],
            "video_metadata": [],
            "compliance_result": []
        }



# Compliance 

def auto_content_node( state: VideoAuditState) -> Dict[str , Any]:
    """
    RAG
    """

    logger.info("----[NODE: Auditor] querying the knowledges based and LLM---")

    transcript = state.get("transcript")
    if not transcript:
        logger.warning("No transcript available ")
        return {
            "error": ["No transcript available for analysis"],
            "final_status": "failed",
            "final_message": "Failed to index video",
            "transcript": "",
            "ocr_text": [],
            "video_metadata": [],
            "compliance_result": []
        }

    # initialising clients 
    
    llm = ChatBedrock(
        model_id=os.getenv("AWS_OPENAI_MODEL"),
        model_kwargs={"temperature": 0.0},
        region_name=os.getenv("REGION")
    )
    embeddings = BedrockEmbeddings(
        model_id=os.getenv("AWS_OPENAI_EMBEDDING_DEPLOYMENT"),
        region_name=os.getenv("REGION")
    )

    # ---- Vector Store (OpenSearch) ----
    vector_store = OpenSearchVectorSearch(
        opensearch_url=os.getenv("OPENSEARCH_ENDPOINT"),
        index_name=os.getenv("OPENSEARCH_INDEX_NAME"),
        embedding_function=embeddings.embed_query,
    )
    
    # rag retrieval

    ocr_text = state.get("ocr_text" , [])
    query_text = f"{transcript} {''.join(ocr_text)}"
    docs = vector_store.similarity_search(query_text , k=5)

    regulation_rules = "\n\n".join([doc.page_content for doc in docs])

    system_prompt = f"""
    You are a Brand Compliance Auditor. Your job is to analyze the video content based on the provided {regulation_rules} and regulations.
    
    You must strictly follow these rules:
    1. Identify any violations of the brand's compliance guidelines.
    2. Provide a clear and concise description of each violation.
    3. Assign a severity level (e.g., "Warning", "Critical").
    4. Suggest specific improvements or actions to rectify the violation.
    5. Base your analysis ONLY on the provided context and transcript.
    
    Return your response in JSON format with the following structure:
    {{
        "compliance_result": [
            {{
                "category": "<category_name>",
                "description": "<description_of_violation>",
                "severity": "<severity_level>",
                "timestamp": "<timestamp_if_available>",
                "suggestion": "<suggestion_for_improvement>"
            }}
        ],
        "final_status": "Passed/Failed/Warning",
        "final_report": "Summary of the audit"
    }}
    """

    user_message = f"""
    VIDEO_METADATA : {state.get("video_metadata")}
    TRANSCRIPT : {state.get("transcript")}
    OCR_TEXT : {state.get("ocr_text")}
    REGULATION_RULES : {regulation_rules}
    """
    
    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt) , HumanMessage(content=user_message)]
        )
        response_content = response.content
        
        if "```" in response_content:
            response_content = re.search(r"```json(.*?)```" , response_content , re.DOTALL).group(1).strip()
        
        data = json.loads(response_content)
        return {
            "compliance_result": data.get("compliance_result" , []),
            "final_status": data.get("final_status" , "failed"),
            "final_report": data.get("final_report" , "Failed to analyze video"),
        }
    except Exception as e:
        logger.error(f"Error in auto_content_node: {str(e)}")
        return {
            "error": [str(e)],
            "final_status": "failed",
            "final_message": "Failed to analyze video",
            "transcript": "",
            "ocr_text": [],
            "video_metadata": [],
            "compliance_result": []
        }



        
        

    
