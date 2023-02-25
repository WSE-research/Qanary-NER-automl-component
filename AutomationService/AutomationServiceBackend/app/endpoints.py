from typing import Dict, List, Optional
from starlette.requests import Request
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from copy import deepcopy
from dotenv import load_dotenv
import logging
import os

from app.model.request_handler import handle_post_api_call, handle_post_retrain_call, handle_get_api_call, \
    handle_get_visualization_call, handle_nlp_call_with_start_and_end, handle_retrain_logging
from app.spacy_model.interact_with_spacy import SpacyInterface
from app.spacy_model.retrain_a_model import ModelRetrainer
from app.helper.filehelper import FileHelper

load_dotenv()

router = APIRouter(
    tags=["endpoints"],
    responses={404: {"description": "Not found"}},
)

logging.getLogger().setLevel(logging.INFO)
interface = SpacyInterface()
trainer = ModelRetrainer()
helper = FileHelper()

use_mlflow = os.getenv('MLFLOW_ACTIVATED')

class Input(BaseModel):
    text: str = Field(
        title="A text that should be identified.", example="I am called Marilyn Monroe."
    )
    language: str = Field(
        default=None, title="A language string.", max_length=2, example="en"
    )
    entities: Dict[str, str] = Field(
        default=None, title="A dictionary of included entities and their labels.",
        example={"First_Name": "Marilyn", "Last_Name": "Monroe"}
    )


class Output(Input):
    results: Dict[str, str] = Field(
        default=None, title="A dictionary of recognized entities and their labels.",
        example={"FIRST_NAME": "Marilyn", "LAST_NAME": "Monroe"}
    )

    class Config:
        orm_mode = True


class Retraindata(BaseModel):
    testingdata: List[Input] = Field(
        title="A list of objects to test the model with."
    )
    trainingdata: List[Input] = Field(
        title="A list of objects to train the model with."
    )
    entities: List[str] = Field(
        title="A list of all entity-labels that the NER model should learn. "
                + "All entities mentioned within the document must be listed here.",
        example=["First_Name", "Middle_Name", "Last_Name"]
    )
    language: str = Field(
        title="The language the new NER model should be based on. ", example="en"
    )
    modeltype: str = Field(
        title="The base model the new NER model should trained on (currently supporting: 'bert', 'spacy'). ",
        example="en"
    )


class SuccessMessage(BaseModel):
    message: str = Field(
        title="A success message.", example="Successfully updated the spacy model based on your uploaded csv data."
    )


@router.get("/api",
            tags=["api"],
            summary="Receive a NER result.",
            response_description="The extracted entities.",
            responses={
                200: {
                    "description": "An example result",
                    "content": {
                        "application/json": {
                            "example": {
                                "text": "I am Marilyn Monroe.",
                                "FIRST_NAME": "Marilyn",
                                "LAST_NAME": "Monroe"
                            }
                        }
                    },
                },
            },
            )
def call_recognition(text: str = 'Text to identify'):
    """
    Receive a JSON object containing the indentified entities and their labels. The form depends on your model. 
    With the default example model, a text to identify could be "I am {YOUR NAME}".
    """
    result = handle_get_api_call(text, interface)
    return result


# Could become an endpoint if needed
def call_recognition_with_entity_position(text: str = 'Text to identify'):
    """
    Receive a JSON object containing the indentified entities and their start and end positions (NOT the labels).
    Empty entities (entities that COULD but are NOT recognized) are not within the result object.
    With the default example model, a text to identify could be "I am {YOUR NAME}".
    """
    result = handle_nlp_call_with_start_and_end(text, interface)
    return result


@router.post("/api",
            tags=["api"],
            summary="Receive a NER result.",
            response_description="The extracted entities.",
            openapi_extra={
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": Input.schema(ref_template="#/components/schemas/{model}")
                            }
                        }
                    }
                }
            },
            responses={
                200: {
                    "description": "An example result",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": Output.schema(ref_template="#/components/schemas/{model}")
                            }
                        },
                        "text/csv": {}
                    },
                }
            })
async def handle_api_call(req: Request, file_to_identify: Optional[UploadFile] = File(None)):
    """
    Generate a NER result of multiple input texts.
    If you enter a csv file, each line must contain the text that shall be identified in the first column.
    If you enter a json file or json request body, it must contain an array in which each element has the
    text that is supposed to be identified with a "text" label.
    Any other wanted columns / objects can be added and will not be changed or removed by the service.
    The result will be the input file annotated with the results.
    Optionally, you can allow MLFlow if you set USE_MLFLOW to True in the .env file. 
    """
    global use_mlflow
    response = await handle_post_api_call(req, interface, helper, file_to_identify,
                                            use_mlflow.lower() in ('true', '1', 't'))
    return response


@router.post("/retrain",
            tags=["retrain"],
            summary="Retrain a model.",
            response_description="A success message.",
            openapi_extra={
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": Retraindata.schema(ref_template="#/components/schemas/{model}")
                        }
                    }
                }
            },
            responses={
                200: {
                    "description": "An example success message",
                    "content": {
                        "application/json": {
                            "schema": SuccessMessage.schema(ref_template="#/components/schemas/{model}")
                        }
                    },
                }
            })
async def handle_retrain_call(req: Request, trainingdata: Optional[UploadFile] = File(None),
                            testingdata: Optional[UploadFile] = File(None),
                            options: Optional[UploadFile] = File(None)):
    """
    Retrain your model in runtime based on your given input. It needs either two CSV files
    (trainingdata and testingdata) with an optional JSON file (options, defaults will be set if none given),
    three JSON files (trainingdata, testingdata and options) or a JSON request body containing all three previously
    mentioned files within one. If correctly structured, the data is used to retrain a new model and overwrite
    the existing one. Optionally, you can allow MLFlow if you set USE_MLFLOW to True in the .env file.
    """
    global use_mlflow
    if use_mlflow.lower() in ('true', '1', 't'):
        log_traindata = deepcopy(trainingdata)
        log_testdata = deepcopy(testingdata)
        log_options = deepcopy(options)

    response = await handle_post_retrain_call(req, trainer, interface, trainingdata, testingdata, options)

    if use_mlflow.lower() in ('true', '1', 't'):
        await handle_retrain_logging(trainer, interface, log_traindata, log_testdata, log_options)
        close_file(log_traindata)
        close_file(log_testdata)
        close_file(log_options)

    close_file(trainingdata)
    close_file(testingdata)
    close_file(options)

    return response


@router.get("/visualize",
            tags=["visualize"],
            summary="Visualize an NER result.",
            response_description="The visualisation as HTML.",
            response_class=HTMLResponse
            )
def get_visual(text: str = 'Text to identify'):
    """
    Receive a JSON object containing the indentified entities and their labels. The form depends on your model. 
    With the default example model, a text to identify could be "I am {YOUR NAME}" with or without the optional
    language string "en".
    """
    result = handle_get_visualization_call(text, interface)
    return result


def close_file(file):
    try:
        file.file.close()
    except:
        pass