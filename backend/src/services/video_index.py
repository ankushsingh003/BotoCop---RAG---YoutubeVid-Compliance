'''
Connector between Python and AWS for video analysis.
'''

import os 
import logging 
import yt_dlp 
import boto3

logger = logging.getLogger("video-indexer")

class VideoIndexerService:
    """
    Service for handling video analysis workflows using AWS (S3, Rekognition) 
    and YouTube integration (yt-dlp).
    """
    def __init__(self):
        self.region = os.getenv("REGION", "eu-north-1")
        
        # Mapping AWS credentials from environment variables
        # Note: Using AWS_STORAGE_CONNECTION_STRING as Access Key and 
        # AWS_OPEN_AI_KEY as Secret Key as per current .ENV configuration
        self.aws_access_key = os.getenv("AWS_STORAGE_CONNECTION_STRING")
        self.aws_secret_key = os.getenv("AWS_OPEN_AI_KEY")
        self.default_bucket = "orchestra00998"

        if not self.aws_access_key or not self.aws_secret_key:
            logger.warning("AWS credentials not fully found in environment variables.")

        # Initialize AWS Session and Clients
        try:
            self.session = boto3.Session(
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.region
            )
            self.s3 = self.session.client("s3")
            self.rekognition = self.session.client("rekognition")
            self.transcribe = self.session.client("transcribe")
            logger.info("AWS clients initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing AWS clients: {e}")
            raise

    def download_youtube_video(self, url: str, output_path: str = "temp_video.mp4") -> str:
        """Downloads a video from YouTube using yt-dlp."""
        logger.info(f"Downloading YouTube video: {url}")
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not os.path.exists(output_path):
                # Fallback if merger failed or output template varied
                if os.path.exists(output_path + ".mp4"):
                    os.rename(output_path + ".mp4", output_path)
                else:
                    raise FileNotFoundError(f"Downloaded file not found at {output_path}")
                    
            return output_path
        except Exception as e:
            logger.error(f"Failed to download YouTube video: {e}")
            raise

    def upload_to_s3(self, local_path: str, video_id: str, bucket: str = None) -> str:
        """Uploads a local file to S3 and returns the S3 URI."""
        bucket = bucket or self.default_bucket
        key = f"videos/{video_id}.mp4"
        
        logger.info(f"Uploading {local_path} to s3://{bucket}/{key}")
        try:
            self.s3.upload_file(local_path, bucket, key)
            return f"s3://{bucket}/{key}"
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    def start_video_analysis(self, bucket: str, video_key: str) -> str:
        """Starts a Rekognition label detection job."""
        logger.info(f"Starting label detection for s3://{bucket}/{video_key}")
        try:
            response = self.rekognition.start_label_detection(
                Video={"S3Object": {"Bucket": bucket, "Name": video_key}}
            )
            return response["JobId"]
        except Exception as e:
            logger.error(f"Failed to start Rekognition analysis: {e}")
            raise

    def get_analysis_results(self, job_id: str):
        """Retrieves results of a Rekognition label detection job."""
        try:
            return self.rekognition.get_label_detection(JobId=job_id)
        except Exception as e:
            logger.error(f"Failed to get Rekognition results: {e}")
            return {}

    def get_insights(self, job_id: str):
        """Alias for get_analysis_results to maintain compatibility with nodes.py."""
        return self.get_analysis_results(job_id)

    def extract_data(self, raw_insights: dict) -> dict:
        """Extracts and cleans relevant data from Rekognition insights."""
        logger.info("Extracting data from Rekognition insights")
        
        if not raw_insights:
            return self._empty_response("No insights data provided")

        labels = raw_insights.get("Labels", [])
        clean_labels = [
            {
                "name": label.get("Label", {}).get("Name"),
                "confidence": label.get("Label", {}).get("Confidence"),
                "timestamp": label.get("Timestamp")
            }
            for label in labels
        ]
        
        # Check JobStatus
        job_status = raw_insights.get("JobStatus", "IN_PROGRESS")
        
        return {
            "transcript": "",  # Placeholder for Transcribe results
            "ocr_text": [],    # Placeholder for Text Detection results
            "video_metadata": clean_labels,
            "final_status": "success" if job_status == "SUCCEEDED" else "processing"
        }

    def _empty_response(self, message: str) -> dict:
        return {
            "transcript": "",
            "ocr_text": [],
            "video_metadata": [],
            "final_status": "failed",
            "message": message
        }

# Alias for backward compatibility with existing code (e.g., nodes.py)
VideoIndexerServices = VideoIndexerService
