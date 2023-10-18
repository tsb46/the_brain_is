import argparse
import json
import numpy as np
import os
import pickle
import spacy

from sentence_transformers import SentenceTransformer
from spacy.matcher import Matcher


# load SpaCy model
model = spacy.load('en_core_sci_lg')
# Initialize Matcher and create matching patterns
matcher = Matcher(model.vocab)

# copula phrase
pattern = [{"POS": 'DET'}, {"LOWER": 'brain', 'DEP': 'nsubj'}, 
           {"LOWER": 'is', 'DEP': 'cop'}, {"POS": 'DET'}]
matcher.add('brain', [pattern])

# copula phrase with adjective modifiers
pattern_human = [{"POS": 'DET'}, {"LOWER": 'human'}, {"LOWER": 'brain', 'DEP': 'nsubj'}, 
               {"LOWER": 'is', 'DEP': 'cop'}, {"POS": 'DET'}]
matcher.add('human_brain', [pattern_human])

pattern_mammal = [{"POS": 'DET'}, {"LOWER": 'mammalian'}, {"LOWER": 'brain', 'DEP': 'nsubj'}, 
               {"LOWER": 'is', 'DEP': 'cop'}, {"POS": 'DET'}]
matcher.add('mammalian_brain', [pattern_mammal])

# load sentence embedding model from HuggingFace
scibert_embed = SentenceTransformer('pritamdeka/S-Scibert-snli-multinli-stsb')


def children_iter(dep, rights):
    # detect dependency relation and get children
    dep_token = [r for r in rights if r.dep_ == dep][0] # get first instance
    end_idx = dep_token.i + 1
    rights = list(dep_token.rights)
    return rights, end_idx


# iterate right w/ nmod or advcl
def phrase_extend(span, doc, match_label):
    # iterate through right children and pick up more of 
    # phrase or any nmod relation
    extend_dep = ('nmod', 'cc', 'acl:relcl')
    # get start indx
    start_idx = span[0].i
    # depending on whether there is an adjectival modifier, the 
    # position of 'is' will change
    if match_label == 'brain':
        cop_verb = span[2] 
    else:
        cop_verb = span[3]

    head = cop_verb.head 
    # get right children
    rights = list(head.rights)
    # set end indx (to be potentially extended)
    end_idx = head.i + 1
    # loop through children and extend phrase
    if len(rights) > 0:
        go_right = True
        while go_right:
            # order matters here
            if 'nmod' in [r.dep_ for r in rights]:
                rights, end_idx = children_iter('nmod', rights)
                if len(rights) == 0:
                    go_right = False
            elif 'conj' in [r.dep_ for r in rights]:
                rights, conj_end_idx = children_iter('conj', rights)
                if len(rights) > 0:
                    end_idx = conj_end_idx
                else:
                    nbor_lefts = list(doc[conj_end_idx].lefts)
                    if len(nbor_lefts) > 0:
                        if nbor_lefts[0] == head:
                            end_idx = conj_end_idx
                    go_right = False
            elif 'acl:relcl' in [r.dep_ for r in rights]:
                rights, end_idx = children_iter('acl:relcl', rights)
                if len(rights) > 0:
                    if 'dobj' in [r.dep_ for r in rights]:
                        rights, end_idx = children_iter('dobj', rights)
                        if len(rights) == 0:
                            go_right = False
                else:
                    go_right = False
            else:
                go_right = False 

    return start_idx, end_idx


def embed_phrase(sents, doi):
    # find phrase and embed
    phrase_embed = []
    for sent in sents:
        doc = model(sent)
        matches = matcher(doc)
        if len(matches) > 0:
            for match_id, start, end in matches:
                string_id = model.vocab.strings[match_id]  # Get string representation
                span = doc[start:end]  # The matched span
                start_idx, end_idx = phrase_extend(span, doc, string_id)
                span_extend = doc[start_idx:end_idx]
                if string_id == 'brain':
                    phrase_text = span_extend.text
                else:
                    # if adjective in front of 'brain', remove (so it doesn't)
                    # influence embedding similarity
                    phrase_text = ' '.join(
                        [t.text for i, t in enumerate(span_extend) if i != 1]
                    )
                embed = scibert_embed.encode(phrase_text)
                phrase_embed.append([doi, span_extend.text, embed])
                 
    return phrase_embed


if __name__ == "__main__":
    """
    Embedding of matched phrases
    """
    parser = argparse.ArgumentParser(description='Embedding of matched phrases')
    parser.add_argument('-i', '--input_json',
                        help='Path to articles containing sentences containing matches',
                        required=True,
                        type=str)

    args_dict = vars(parser.parse_args())
    

    articles = json.load(open(args_dict['input_json']))
    embeddings = []
    for i, a in enumerate(articles):
        if i % 100 == 0:
            print(f"{i} articles processed")
        embed = embed_phrase(a['matched_sent'], a['doi'])
        embeddings.append(embed)

    # flatten list
    embeddings = [e for e_list in embeddings for e in e_list]
        
    # write to json
    pickle.dump(embeddings, open(f'phrase_embeddings.pkl', 'wb'))




