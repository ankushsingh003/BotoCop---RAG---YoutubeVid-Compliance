import os
import torch
from dotenv import load_dotenv

load_dotenv()

def get_device() -> torch.device:
    """
    Returns the torch device. 
    Defaults to the value of TORCH_DEVICE environment variable if available and valid.
    Falls back to 'cuda' if a GPU is available, otherwise 'cpu'.
    """
    preferred_device = os.getenv("TORCH_DEVICE", "cuda").lower()
    
    if preferred_device == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    
    if preferred_device == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
        
    return torch.device("cpu")

if __name__ == "__main__":
    device = get_device()
    print(f"Active Device: {device}")
    if device.type == "cuda":
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
