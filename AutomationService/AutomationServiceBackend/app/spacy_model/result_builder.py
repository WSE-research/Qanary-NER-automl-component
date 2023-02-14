import logging
import os
import spacy
from spacy.cli import download
from enum import Enum

class ResultBuilder:

    nlp = None

    def __init__(self):
        logging.info("Result builder initialized.")
        #if self.nlp == None:
        #    self.reload_language_model("")

    def reload_language_model(self, language):
        new_nlp = None
        model = ""
        if 'BASE_' + language in os.environ:
            model = os.environ['BASE_' + language]
        else:
            logging.warning(f"No base model found for language {language} to build results with. A default English model will be used. (This is ONLY for the result building and not the actual classification)")
            model = os.environ['BASE_EN']

        try:
            new_nlp = self.ensure_model_exists(model)
            self.nlp = new_nlp
            logging.info("Successfully reloaded the model for result building")
        except:
            logging.error("Reloading of the result builder model has failed.")

    def ensure_model_exists(self, model):
        try:
            try:
                logging.info("Attempting reloading of " + model)
                return spacy.load(model)
            except:
                logging.info("Attempting download of " + model)
                download(model)
                logging.info("Download successful. Attempting reloading of " + model)
                return spacy.load(model)
        except:
            logging.error('No downloadable model found for the Result Building Process.')
        
    #needed?
    def initialize_empty_result_object(self, labels):
        result = {}
        for entity in labels:
            result[entity] = ""
        return result

    def get_connected_tokens(self, doc):
        """
        From a given list of Tokens, generate a new list where tokens in a compound relation are moved into their own list. Tokens without compound relations will be in a list with only themselves
        """
        compounds = []
        for tok in doc:
            if tok.dep_ != "compound":
                token_list = [tok.text]
                for child in tok.children:
                    if child.dep_ == "compound":
                        token_list.append(child.text)
                compounds.append(token_list)
        return compounds
        

    def get_token_to_ent(self, ent, tokens):
        """
        Returns the token list containing the content of an entity based on string matching
        """
        for list in tokens:
            for item in list:
                if ent == item or ent is item or ent in item:
                    return list
        return None

    def build_result_list(self, recognition_doc, labels, use_span = False):
        """
        Build a result object based on a given input doc
        The compound relationship extracted using spacy's base models is used to determine connected individuals
        """
        # Build a list of connected tokens based on a general model
        doc = self.nlp(recognition_doc.text)
        tokens = self.get_connected_tokens(doc)
        print(tokens)
        result_list = []
        result_object = self.initialize_empty_result_object(labels=labels)

        entities = []
        for entity in recognition_doc.ents:
            entities.append(entity.text)
        # Iterate over recognized entities
        for outer_entity in recognition_doc.ents:
            outer_content = outer_entity.text

            # Grab a Token list that contains the recognized entity content (e.g. a name)
            token_list_with_entity = self.get_token_to_ent(outer_content, tokens)
            if(token_list_with_entity != None):
                # Remove the token
                tokens.remove(token_list_with_entity)

                # Reiterate over recognized entities
                for inner_entity in recognition_doc.ents:
                    inner_content = inner_entity.text

                    # If another entity is found that is contained in the token list, add it to the result object
                    if inner_content in token_list_with_entity:
                        # If multiple have been recognized, merge them
                        result_object = self.update_result_object(inner_entity, result_object, use_span)
                        token_list_with_entity.remove(inner_content)
                        entities.remove(inner_content)
                    if len(token_list_with_entity) == 0:
                        continue
            # If entity is not found in tokens and has not been added to another object already (is still within the entity list), save as alone standing
            elif token_list_with_entity == None and outer_content in entities:
                result_object = self.update_result_object(outer_entity, result_object, use_span)
                entities.remove(outer_content)
            # If entity is not found in tokens and has been stored in another object (is not in entity list), do nothing
            else: 
                continue
            result_list.append(result_object)
            result_object = self.initialize_empty_result_object(labels)
    
        return result_list

    def update_result_object(self, entity, result_object, use_span):
        label = entity.label_
        content = entity.text
        print(f"{label}: {content}")
        if use_span:
            content = {
                'start': entity.start_char,
                'end': entity.end_char
            }
        return self.add_content_to_result_object(label, content, result_object)

    def add_content_to_result_object(self, label, content, result_object):
        #Initial label can be filled even though it might exist 
        counter = 1
        if label in result_object and result_object[label] != "":
            label_discovered = False
            while not label_discovered:
                #If label exists and is not 
                if f"{label}_{counter}" in result_object:
                    counter += 1
                else:
                    result_object[f"{label}_{counter}"] = content
                    label_discovered = True
        else:
            result_object[label] = content
        return result_object