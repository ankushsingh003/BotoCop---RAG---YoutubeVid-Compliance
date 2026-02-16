import os
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("botocop-web")

app = FastAPI(title="BotoCop Web API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Model
class AuditRequest(BaseModel):
    video_url: str

@app.post("/api/audit")
async def run_audit(request: AuditRequest):
    try:
        # Lazy load the heavy graph only when needed
        logger.info("Importing video audit graph...")
        from backend.src.graph.workflow import video_audit_graph
        
        session_id = str(uuid.uuid4())
        logger.info(f"Audit requested for: {request.video_url} (Session: {session_id})")
        
        input_data = {
            "video_url": request.video_url,
            "video_id": session_id[:8],
            "compliance_result": [],
            "error": []
        }
        
        # Invoke the graph
        result = video_audit_graph.invoke(input_data)
        
        return {
            "success": result.get("final_status") == "success",
            "video_id": result.get("video_id"),
            "status": result.get("final_status"),
            "report": result.get("final_report", "No report generated"),
            "issues": result.get("compliance_result", []),
            "errors": result.get("error", [])
        }
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Basic health check
@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# Serve Frontend
# server.py is in backend/src/api/
# static is in backend/static/
static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static"))
if not os.path.exists(static_path):
    os.makedirs(static_path)

logger.info(f"Serving static files from: {static_path}")
app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
