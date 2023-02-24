import json
import os
import uuid
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from qanary_helpers.qanary_queries import insert_into_triplestore, get_text_question_in_graph
from qanary_helpers.registration import Registration
from qanary_helpers.registrator import Registrator
import logging

from app.endpoints import router, call_recognition_with_entity_position
from app.model.MLFlowLogging import MLFlowLoggerFactory

if not os.getenv("PRODUCTION"):
    from dotenv import load_dotenv

    load_dotenv()  # required for debugging outside Docker

SPRING_BOOT_ADMIN_URL = os.environ['SPRING_BOOT_ADMIN_URL']
SPRING_BOOT_ADMIN_USERNAME = os.environ['SPRING_BOOT_ADMIN_USERNAME']
SPRING_BOOT_ADMIN_PASSWORD = os.environ['SPRING_BOOT_ADMIN_PASSWORD']
SERVICE_HOST = os.environ['SERVICE_HOST']
SERVICE_PORT = os.environ['SERVICE_PORT']
SERVICE_NAME_COMPONENT = os.environ['SERVICE_NAME_COMPONENT']
SERVICE_DESCRIPTION_COMPONENT = os.environ['SERVICE_DESCRIPTION_COMPONENT']
# While using server with permanent external IP address: URL_COMPONENT = f"http://{SERVICE_HOST}:{SERVICE_PORT}"
URL_COMPONENT = f"{SERVICE_HOST}"

app = FastAPI()
ml_logger = MLFlowLoggerFactory.get_ml_logger()
app.include_router(router)

logging.basicConfig(level=logging.INFO)


@app.post("/annotatequestion")
async def qanary_service(request: Request):
    request_json = await request.json()
    triplestore_endpoint_url = request_json["values"]["urn:qanary#endpoint"]
    triplestore_ingraph_uuid = request_json["values"]["urn:qanary#inGraph"]

    # get question text from triplestore
    question_text = get_text_question_in_graph(
        triplestore_endpoint_url, triplestore_ingraph_uuid)[0]['text']
    question_uri = get_text_question_in_graph(triplestore_endpoint=triplestore_endpoint_url,
                                              graph=triplestore_ingraph_uuid)[0]['uri']

    nlp_result = call_recognition_with_entity_position(question_text)

    # No creation query needed, only question:
    sparql_query = question_text

    annotations = ''

    for result in nlp_result["result"]:
        counter = 0
        for entity in result:
            run_id = uuid.uuid1()
            entityid = f"urn:{entity}:{run_id}"
            start = result[entity]['start']
            end = result[entity]['end']
            annotations = """
                        {annotations}
                        ?entityAnnotation{counter} a qa:AnnotationOfInstance .
                        ?entityAnnotation{counter} oa:hasTarget [
                            a   oa:SpecificResource;
                                oa:hasSource    <{question_uri}> ;
                                oa:hasSelector  [
                                    a oa:TextPositionSelector ; 
                                    oa:start "{start}"^^xsd:nonNegativeInteger ; 
                                    oa:end  "{end}"^^xsd:nonNegativeInteger 
                                ]
                            ] .
                        ?entityAnnotation{counter} oa:hasBody "{entity}"^^xsd:string ; 
                            oa:annotatedBy <urn:qanary:automl:{component}> ; 
                            oa:annotatedAt ?time ;
                            qa:score "0.5"^^xsd:decimal .
            """.format(annotations=annotations,
                        question_uri=question_uri,
                        entityid=entityid,
                        entity=entity,
                        start=start,
                        end=end,
                        component=SERVICE_NAME_COMPONENT.replace(" ", "-"),
                        counter=counter)
            counter += 1

    binds = ''
    for i in range(counter):
        binds = """
                    {binds}
                        BIND (IRI(str(RAND())) AS ?entityAnnotation{number}) .
                """.format(
            binds=binds,
            number=i
        )

    # and this "generated" query is stored in the triplestore with this INSERT query:
    SPARQLquery = """
                    PREFIX dbr: <http://dbpedia.org/resource/>
                    PREFIX dbo: <http://dbpedia.org/ontology/>
                    PREFIX qa: <http://www.wdaqua.eu/qa#>
                    PREFIX oa: <http://www.w3.org/ns/openannotation/core/>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    INSERT {{
                    GRAPH <{uuid}> {{
                        {annotations}
                        }}
                    }}
                    WHERE {{
                        {binds}
                        BIND (now() as ?time) 
                    }}
                """.format(
        annotations=annotations,
        uuid=triplestore_ingraph_uuid,
        binds=binds,
        question_uri=question_uri,
        component=SERVICE_NAME_COMPONENT.replace(" ", "-"),
        sparql_query=sparql_query.replace("\n", "\\n").replace("\"", "\\\""))

    insert_into_triplestore(triplestore_endpoint_url,
                            SPARQLquery)  # inserting new data to the triplestore

    if(ml_logger != None):
        run_uuid = uuid.uuid1()
        ml_logger.log_annotation(run_uuid, question_text, json.dumps(
            nlp_result["result"]), triplestore_ingraph_uuid)

    return JSONResponse(content=request_json)


@app.get("/health")
def health():
    return PlainTextResponse(content="alive")


metadata = {
    "start": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "description": SERVICE_DESCRIPTION_COMPONENT,
    "written in": "Python"
}

registration = Registration(
    name=SERVICE_NAME_COMPONENT,
    serviceUrl=f"{URL_COMPONENT}",
    healthUrl=f"{URL_COMPONENT}/health",
    metadata=metadata
)

reg_thread = Registrator(SPRING_BOOT_ADMIN_URL, SPRING_BOOT_ADMIN_USERNAME,
                         SPRING_BOOT_ADMIN_PASSWORD, registration)
reg_thread.daemon = True
reg_thread.start()

if __name__ == "__main__":
    logging.info("name: " + SERVICE_NAME_COMPONENT)
    logging.info("description: " + SERVICE_DESCRIPTION_COMPONENT)
    logging.info("host: " + SERVICE_HOST)
    logging.info("port: " + SERVICE_PORT)
    logging.info("Qanary System: Spring Boot admin url: " +
                 SPRING_BOOT_ADMIN_URL)
    uvicorn.run(app, host="0.0.0.0", port=int(SERVICE_PORT))
