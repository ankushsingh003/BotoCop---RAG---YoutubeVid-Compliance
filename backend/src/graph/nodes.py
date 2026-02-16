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
    
    """

    logger
