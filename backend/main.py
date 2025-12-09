import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv
from urllib.parse import quote_plus
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Get MongoDB credentials
username = os.getenv("MONGO_USERNAME")
password = os.getenv("MONGO_PASSWORD")
cluster = os.getenv("MONGO_CLUSTER")
DB_NAME = os.getenv("MONGO_DB_NAME", "mydatabase")

if not all([username, password, cluster]):
    raise RuntimeError("Please set MONGO_USERNAME, MONGO_PASSWORD, and MONGO_CLUSTER in .env file")

# Create properly encoded MongoDB URI
MONGODB_URI = f"mongodb+srv://{quote_plus(username)}:{quote_plus(password)}@{cluster}/?retryWrites=true&w=majority"

# Connect to MongoDB using synchronous client (better for serverless)
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Initialize FastAPI
app = FastAPI(title="RakshakAI Multi-Collection API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------
# MODELS
# ----------------------------------------

class Driver(BaseModel):
    name: str
    status: str
    latitude: float
    longitude: float

class PatientLocation(BaseModel):
    location: str
    latitude: float
    longitude: float

class Emergency(BaseModel):
    call_id: str
    status: str
    driver: Driver
    patient: PatientLocation

class PatientInfo(BaseModel):
    name: str
    date: str
    duration: str

class MedicalRecord(BaseModel):
    call_id: str
    patient_information: PatientInfo
    chief_complaint: str
    reported_symptoms: List[str]
    ai_analysis: str
    recommended_specialty: str

class UserLocation(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    timestamp: Optional[str] = None

# ----------------------------------------
# ROUTES
# ----------------------------------------

@app.post("/user_location")
def save_user_location(payload: UserLocation):
    """Save user location to database"""
    try:
        collection = db["user_locations"]
        try:
            payload_dict = payload.model_dump(mode='json')
        except (AttributeError, TypeError):
            payload_dict = payload.dict()

        # Add timestamp if not provided
        if not payload_dict.get("timestamp"):
            from datetime import datetime
            payload_dict["timestamp"] = datetime.now().isoformat()

        # Upsert based on user_id
        result = collection.update_one(
            {"user_id": payload.user_id},
            {"$set": payload_dict},
            upsert=True
        )
        return {
            "message": "User location saved successfully",
            "user_id": payload.user_id,
            "updated": result.modified_count > 0,
            "created": result.upserted_id is not None
        }
    except Exception as e:
        print(f"Error in /user_location: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/user_location/{user_id}")
def get_user_location(user_id: str):
    """Get user location from database"""
    try:
        collection = db["user_locations"]
        location = collection.find_one({"user_id": user_id})

        if not location:
            raise HTTPException(status_code=404, detail="User location not found")

        # Convert ObjectId to string
        if "_id" in location:
            location["_id"] = str(location["_id"])

        return location
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /user_location/{user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/emergency_detected")
def create_emergency_record(payload: Emergency):
    try:
        collection = db["emergency"]
        # Use model_dump with mode='json' for proper serialization
        try:
            payload_dict = payload.model_dump(mode='json')
        except (AttributeError, TypeError):
            payload_dict = payload.dict()
        result = collection.insert_one(payload_dict)
        # Don't include _id in response data to avoid ObjectId serialization issues
        return {"message": "Emergency record stored successfully", "call_id": payload.call_id, "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error in /emergency_detected: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/medical_record")
def create_medical_record(payload: MedicalRecord):
    try:
        collection = db["medical_record"]
        # Use model_dump with mode='json' for proper serialization
        try:
            payload_dict = payload.model_dump(mode='json')
        except (AttributeError, TypeError):
            payload_dict = payload.dict()
        result = collection.insert_one(payload_dict)
        # Don't include _id in response data to avoid ObjectId serialization issues
        return {"message": "Medical record stored successfully", "call_id": payload.call_id, "id": str(result.inserted_id)}
    except Exception as e:
        print(f"Error in /medical_record: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/status")
def get_status(call_id: str = Query(..., description="Unique call ID")):
    try:
        emergency_col = db["emergency"]
        medical_col = db["medical_record"]

        emergency_data = emergency_col.find_one({"call_id": call_id})
        medical_data = medical_col.find_one({"call_id": call_id})

        if not emergency_data and not medical_data:
            raise HTTPException(status_code=404, detail="No records found for this call_id")

        # Convert ObjectId to string
        if emergency_data and "_id" in emergency_data:
            emergency_data["_id"] = str(emergency_data["_id"])
        if medical_data and "_id" in medical_data:
            medical_data["_id"] = str(medical_data["_id"])

        return {
            "call_id": call_id,
            "emergency_details": emergency_data or "No emergency data",
            "medical_record_details": medical_data or "No medical record data"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in /status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/")
def home():
    return {"message": "Welcome to RakshakAI Emergency & Medical Record API", "version": "v2.1-pydantic-fix"}

@app.get("/debug")
def debug():
    """Debug endpoint to check MongoDB connection"""
    try:
        # Try to ping MongoDB
        client.admin.command('ping')
        return {
            "mongodb_connected": True,
            "database": DB_NAME,
            "env_vars_set": {
                "MONGO_USERNAME": bool(os.getenv("MONGO_USERNAME")),
                "MONGO_PASSWORD": bool(os.getenv("MONGO_PASSWORD")),
                "MONGO_CLUSTER": bool(os.getenv("MONGO_CLUSTER")),
                "MONGO_DB_NAME": bool(os.getenv("MONGO_DB_NAME"))
            }
        }
    except Exception as e:
        return {
            "mongodb_connected": False,
            "error": str(e),
            "env_vars_set": {
                "MONGO_USERNAME": bool(os.getenv("MONGO_USERNAME")),
                "MONGO_PASSWORD": bool(os.getenv("MONGO_PASSWORD")),
                "MONGO_CLUSTER": bool(os.getenv("MONGO_CLUSTER")),
                "MONGO_DB_NAME": bool(os.getenv("MONGO_DB_NAME"))
            }
        }
