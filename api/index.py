import sys
import os

# Ensure parent directory is in Python path so app modules load properly on Vercel
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
