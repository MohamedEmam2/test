from firebase_functions import https_fn,options
from functions_wrapper import entrypoint
import pycountry
from flask import Flask, request, jsonify, abort
from pydantic import BaseModel, ValidationError
from Agent.utils import *
import json
import copy
import logging
import firebase_admin
from firebase_admin import credentials
from Agent import Agent
from lingua import LanguageDetectorBuilder, Language

# Initialize Firebase Admin
cred = credentials.Certificate("./creds/maike-b9a3f-firebase-adminsdk-z5ytp-b4dfcb4561.json")
firebase_admin.initialize_app(cred)

# Initialize Flask app and agent
app = Flask(__name__)

@https_fn.on_request(cors=options.CorsOptions(cors_origins="*", cors_methods=["get", "post"]),secrets=None,region="europe-west1", memory=1024*2, timeout_sec=400)
def Maike_Agent(request):
    return entrypoint(app, request)

agent = Agent()
class AgentRequest(BaseModel):
    Payload: dict 
    CITY_ID: str 
print("initalize agent")
# Define request body schema

@app.route("/ask_agent", methods=["POST"])
def ask_agent():
    try:

        response={
                    "files_states": {},
                    "websites_states": {},
                    "files_names": [],
                    "websites_names": [],
                    "photos_states": {},
                    "photos": [],
                    "agentResponse": {},
                    "city_state": ""
                    
                }    

        # Parse and validate request
        if not request.is_json:
            abort(400, description="Invalid JSON body in the request.")

        try:
            data = request.get_json()
            logging.info(f"Received data: {data}")
            if not isinstance(data, dict):
                raise ValueError("Request body must be a JSON object.")

            data_payload = data.get("Payload")
            city_id = data.get("CITY_ID")

            if not data_payload or not isinstance(data_payload, dict):
                raise ValueError("Payload must be a valid JSON object.")

            if not city_id or not isinstance(city_id, str):
                raise ValueError("CITY_ID must be a string.")
        except ValueError as e:
            abort(400, description=f"Invalid input: {str(e)}")

        # Extract data_payload
        queries = data_payload.get("agentText",[{}])
        location = data_payload.get("location",{})
        photo = data_payload.get("agentPhotos")
        city =city_id
        user_lang=data_payload.get("user_lang")
        if not queries or not isinstance(queries, list):
            logging.warning("no query are sened")
        history = ""
        query=""
        
        if (isinstance(queries, list) and len(queries)>0) and queries!=[{}]:
            query = queries[-1].get("content","")
            if queries[-1].get("role")!="user":
                logging.info("last query role isn't user")

            for row in queries[:-1]:
                history += f"{row.get('role')}: {row.get('content')}\n"

        # Handle photo (if provided)
        image = photo.get("content", "")
        ext = photo.get("ext", "")
        if image and len(image) > 5 * 1024 * 1024:  # Check for 5MB limit
            abort(400, description="Image size exceeds 5MB.")
        try:

            if image:
                if  query=="" or not query or query==None:
                    query=f"come visitare questo posto nell'immagine"
                    """
                    if history:
                        lang_query=""
                    else:
                            lang_query="English"""
                logging.info("query",query)                
                answer,lang = agent.ask_MultiModel_Agent(query, location, history, image, ext, city,user_lang)
            else:
                    
                answer,lang = agent.ask_TextOnly_Agent(query, location, history, city)
            response["lang_detect"]=lang
            print("answer",answer)
            response[ "agentResponse"] = [
                {
                    "role":"user",
                        "content": query,
                    }   ,
                {
                    "role":"assistant",
                    "content":answer["output"]  
                }                               
            ]
            logging.info("Request endned")
            return jsonify(response)
        except Exception as e:
             logging.error(e)
             response["lang_detect"]="en"

            # Format and return respon
             response[ "agentResponse"] = [
                {
                    "role":"user",
                        "content": query,
                    }   ,
                {
                    "role":"assistant",
                    
                    "content":"sorry we can't provide any information now please try later",
                }                               
            ]
             return jsonify(response)

    except json.JSONDecodeError:
        abort(400, description="Invalid JSON body in the request.")
    except Exception as e:
        logging.error(f"Error: {e}")
        
        abort(500, description=f"An error occurred: {str(e)}")