import argparse
import json
import os
import spacy

from glob import glob
from multiprocessing.pool import Pool
from spacy.matcher import Matcher
from tqdm import tqdm


# entity strings for search entities
# load entity strings
with open('entity_strings.txt', 'r') as file:
    entities = [line.rstrip() for line in file]

# load SpaCy model
model = spacy.load('en_core_sci_lg')
# Initialize Matcher and create matching patterns
matcher = Matcher(model.vocab)


# create phrase patterns to match on 
for e in entities:
    # copula phrase
    pattern = [
        {"POS": 'DET'}, 
        {"LOWER": e, 'DEP': 'nsubj'}, 
        {"LOWER": {"IN": ['is', 'are']}, 'DEP': 'cop'}, 
        {"POS": 'DET'}
    ]
    matcher.add(e, [pattern])
    # copula phrase with adjective modifier
    pattern_adj = [
        {"POS": 'DET'}, 
        {"POS": 'ADJ'}, 
        {"LOWER": e, 'DEP': 'nsubj'}, 
        {"LOWER": {"IN": ['is', 'are']}, 'DEP': 'cop'}, 
        {"POS": 'DET'}
    ]
    matcher.add(f'{e}_adj', [pattern_adj])


def find_matches(article):
    if 'text' in article:
        text = article['text']
    else:
        text = {'abstract': article['abstract']}

    sents = find_sentences(text)
    if len(sents) > 0:
        article['matched_sent'] = sents
        return article


def find_sentences(article_text):
    sent = []
    for sec in article_text:
        doc = model(article_text[sec])
        matches = matcher(doc)
        if len(matches) > 0:
            for match_id, start, end in matches:
                string_id = model.vocab.strings[match_id]  # Get string representation
                span = doc[start:end]  # The matched span
                sent.append(span.sent.text)
    return sent


if __name__ == "__main__":
    """
    Extract articles containing entity terms
    """
    parser = argparse.ArgumentParser(description='Extract articles matching token pattern')
    parser.add_argument('-i', '--input_folder',
                        help='Path to folder containing parsed pubmed articles in .json format',
                        required=True,
                        type=str)
    parser.add_argument('-n', '--n_processes',
                        help='number of processes in parallel pool',
                        default=8,
                        required=False,
                        type=int)
    args_dict = vars(parser.parse_args())

    # create parallel pool
    pool = Pool(processes=args_dict['n_processes'])

    fp_jsons = glob(os.path.join(args_dict['input_folder'], '*.json'))
    found_articles_all = []
    for fp in fp_jsons:
        articles = json.load(open(fp))
        pool_iter = pool.imap_unordered(func=find_matches, iterable=articles)
        found_articles = []
        print(fp)
        for article in tqdm(pool_iter, total=len(articles)):
            if article is not None:
                found_articles.append(article)
        found_articles_all.append(found_articles)

    # flatten list
    found_articles_all = [f for f_dir in found_articles_all for f in f_dir]
        
    # write to json
    json.dump(found_articles_all, open(f'matched_articles.json', 'w'), indent=4)




