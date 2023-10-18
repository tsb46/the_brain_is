import argparse
import json
import os
import spacy
import pubmed_parser as pp

from glob import glob
from multiprocessing import Pool
from tqdm import tqdm

# entity strings for search entities
# load entity strings
with open('entity_strings.txt', 'r') as file:
    entities = [line.rstrip() for line in file]

# load SpaCy model
exclude_pipes = ['tok2vec', 'parser']
model = spacy.load('en_core_sci_sm', exclude=exclude_pipes)

def parse_xml(fp):
    p_docs = pp.parse_pubmed_paragraph(fp)
    p_meta = pp.parse_pubmed_xml(fp)
    p_docs.append(
      {
        'section': 'abstract',
        'text': p_meta['abstract']
      }
    )
    return p_docs, p_meta


def find_article_ents(fp):
    try:
        p_docs, p_meta = parse_xml(fp)
    # an unknown # of files fail the xml pubmed parser (xml objects can't be read)
    except:
        return None
    full_text = {}
    for d in p_docs:
        if len(d['text']) < 1000000:
            doc = model(d['text'])
            if any([e.lemma_.lower() in entities for e in doc.ents]):
                if d['section'] in full_text:
                    full_text[d['section']] = \
                    ' '.join([full_text[d['section']], d['text']])
                else:
                    full_text[d['section']] = d['text']
    if bool(full_text):
        p_meta['text'] = full_text
        return p_meta



if __name__ == "__main__":
    """
    Extract articles containing entity terms
    """
    parser = argparse.ArgumentParser(description='Extract articles containing entity terms')
    parser.add_argument('-p', '--pmc_folder',
                        help='<Required> path to PMC folder to extract articles from',
                        required=True,
                        type=str)
    parser.add_argument('-n', '--n_processes',
                        help='number of processes in parallel pool',
                        default=8,
                        required=False,
                        type=int)
    args_dict = vars(parser.parse_args())

    # get passed arguments
    n_proc = args_dict['n_processes']
    pmc_path = args_dict['pmc_folder']
    pmc = os.path.basename(pmc_path)
    

    # get .xml articles in PMC directory
    fps = glob(f'{pmc_path}/*.xml')

    # loop through articles in PMC directory and find those containing entities
    pool = Pool(processes=n_proc)
    found_articles = []
    for article in tqdm(pool.imap_unordered(func=find_article_ents, iterable=fps), 
                        total=len(fps)):
        found_articles.append(article)
    # filter out null entries
    found_articles_filt = [f for f in found_articles if f is not None]
    # write to json
    json.dump(found_articles_filt, open(f'{pmc}.json', 'w'), indent=4)




