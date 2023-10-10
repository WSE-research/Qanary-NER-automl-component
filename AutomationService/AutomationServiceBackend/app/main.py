from fastapi import FastAPI
from .endpoints import router
from fastapi.middleware.cors import CORSMiddleware

description = """
This Automation Service can **automatically generate a NER model** and offer an endpoint to interact with it.

If **training and testing-data** is provided and no existing model was uploaded, this service will train and 
use a brand new model for you!
You will be able to send a text to the **\\api endpoint** and receive the NER result for the given text!
You can also send multiple texts and files to that endpoint to have them annotated with the results.
The **\\retrain endpoint** allows you to retrain your model run-time!
"""
tags_metadata = [
    {
        "name": "api",
        "description": "Allows to retrieve NER result of a given input text. Will return the recognized "
                        "entities and their labels. If larger quantities are uploaded, it allows to annotate an "
                        "uploaded CSV file/JSON file/ JSON request body with NER results. A CSV file must have "
                        "texts to identify in the first column whilst a json file must consist of an array where "
                        "each object has the text to identify with the label \"text\"",
    },
    {
        "name": "retrain",
        "description": "Allows to retrain the NER model based on a given input. The old one will be overwritten."
    }
]

app = FastAPI(
    title="AutomationService",
    description=description,
    version="0.0.1",
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(router)
