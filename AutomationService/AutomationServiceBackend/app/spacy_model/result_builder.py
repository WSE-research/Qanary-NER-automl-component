import logging
import os
import spacy
from spacy.cli import download
from enum import Enum
import re

class ResultBuilder:

    # Tags to use for building the compound lists
    # tag_list suitable for English and German models
    tag_list = ["compound", "nmod", "nummod", "pnc", "nk", "nmc"]

    nlp = None

    def __init__(self):
        logging.info("Result builder initialized.")
        #if self.nlp == None:
        #    self.reload_language_model("")

    def reload_language_model(self, language):
        new_nlp = None
        model = ""
        if 'BASE_' + language.upper() in os.environ:
            model = os.environ['BASE_' + language.upper()]
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

    def transform_compounds_to_entity_string(self, doc, compounds):
        token_strings = []
        for i in range(len(doc)):
            current_token = doc[i].text
            token_list = self.get_token_to_ent(current_token, compounds)
            if token_list is not None:
                compounds.remove(token_list)
                token_string = ""
                for j in range(i, len(doc)): #iterate over token list from current position onwards to generate the entity string
                    doc_text = doc[j].text
                    if doc_text in token_list:
                        token_list.remove(doc_text)
                        token_string += doc_text
                        if j < len(doc) - 1 and doc[j+1].dep_ == "punct":
                            token_string = token_string + doc[j+1].text
                        else:
                            token_string = token_string + " "
                    if len(token_list) == 0:
                        continue
                if (token_string != ""):
                    token_strings.append(token_string)
        return token_strings 


    def get_connected_tokens_as_string(self, doc):
        """
        From a given list of connected tokens, generate a new list where tokens are merged into strings
        """
        compounds = self.get_connected_tokens(doc)
        lists = self.transform_compounds_to_entity_string(doc, compounds)
        return lists
            
    #needed?
    def initialize_empty_result_object(self, labels):
        result = {}
        for entity in labels:
            result[entity] = ""
        return result
    
    def recursively_grab_children(self, token, token_list):
        for child in token.children:
            if child.dep_ in self.tag_list:
                token_list.append(child.text)
                token_list = self.recursively_grab_children(child, token_list)
        return token_list

    def get_connected_tokens(self, doc):
        """
        From a given list of Tokens, generate a new list where tokens in a compound relation are moved into their own list. Tokens without compound relations will be in a list with only themselves
        """
        compounds = []
        for tok in doc:
            if tok.dep_ not in self.tag_list:
                token_list = [tok.text]
                token_list = self.recursively_grab_children(tok, token_list)

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

    def get_token_string_to_ent(self, ent, tokens):
        """
        Returns the token list containing the content of an entity based on string matching
        """
        for string in tokens:
            if re.search(r"(^|[\?\.!\- \,])" + re.escape(ent) + r"([\?\.!\- \,]|$)", string):
                return string
        return None
    
    def build_result_list_simple(self, recognition_doc, labels, use_span = False):
        """
        Build a result object without regards to POS tags
        """ 
        result_list = []
        result_object = self.initialize_empty_result_object(labels=labels)

        for entity in recognition_doc.ents: 
            label = entity.label_
            if result_object[label] == "":
                result_object = self.update_result_object(entity, result_object, use_span)
            else:
                result_list.append(result_object)
                result_object = self.initialize_empty_result_object(labels=labels)
                result_object = self.update_result_object(entity, result_object, use_span)
        result_list.append(result_object)
        return result_list

    def build_result_list(self, recognition_doc, labels, use_span = False):
        """
        Build a result object based on a given input doc
        The compound relationship extracted using spacy's base models is used to determine connected individuals
        """
        # Build a list of connected tokens based on a general model
        doc = self.nlp(recognition_doc.text)
        token_strings = self.get_connected_tokens_as_string(doc)
        result_list = []
        result_object = self.initialize_empty_result_object(labels=labels)

        entities = []
        for entity in recognition_doc.ents:
            entities.append(entity.text)
        # Iterate over recognized entities
        for outer_entity in recognition_doc.ents:
            outer_content = outer_entity.text

            # Grab a Token list that contains the recognized entity content (e.g. a name)
            token_string_for_entity = self.get_token_string_to_ent(outer_content, token_strings)
            if(token_string_for_entity != None):
                # Remove the token
                token_strings.remove(token_string_for_entity)
                # Reiterate over recognized entities
                for inner_entity in recognition_doc.ents:
                    inner_content = inner_entity.text

                    # Make sure the entity is more than whitespaces and punctuations
                    control_string = re.sub('[^A-Za-z0-9]+', '', inner_content) 

                    # If another entity is found that is contained in the token list, add it to the result object
                    if re.search(r"(^|[\?\.!\- \,])" + re.escape(inner_content) + r"([\?\.!\- \,]|$)", token_string_for_entity) and control_string != "":
                        # If multiple have been recognized, merge them
                        result_object = self.update_result_object(inner_entity, result_object, use_span)
                        token_string_for_entity = token_string_for_entity.replace(inner_content, "")
                        if inner_content not in entities:
                            logging.warn(f"Unexpected entity found: {inner_content}; It is connected to the leftover string \"{token_string_for_entity}\". The left entity list is:")
                            logging.warn(entities)
                            continue
                        entities.remove(inner_content)
                    if len(token_string_for_entity) == 0:
                        continue
            # If entity is not found in tokens and has not been added to another object already (is still within the entity list), save as alone standing
            elif token_string_for_entity == None and outer_content in entities:
                result_object = self.update_result_object(outer_entity, result_object, use_span)
                entities.remove(outer_content)
            # If entity is not found in tokens and has been stored in another object (is not in entity list), do nothing
            else: 
                continue
            result_list.append(result_object)
            result_object = self.initialize_empty_result_object(labels)
        #if (len(result_list) == len(recognition_doc.ents)):
        #    result_list = self.build_result_list_simple(recognition_doc, labels, use_span)
    
        return result_list

    def update_result_object(self, entity, result_object, use_span):
        label = entity.label_
        content = entity.text
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