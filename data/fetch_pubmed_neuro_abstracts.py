import argparse
import datetime
import json
import os
import pubmed_parser as pp
import requests
import time

from lxml import html, etree
from multiprocessing.pool import ThreadPool as Pool
from requests.exceptions import ChunkedEncodingError, HTTPError, ConnectionError
from time import sleep



fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
rate_limit = 10


def exceeded_rate_limit(requestsMade):
    """ 
    Copied from: https://github.com/gijswobben/pymed/blob/master/pymed/api.py#L22
    Helper method to check if we've exceeded the rate limit.
    """

    # Remove requests from the list that are longer than 1 second ago
    requestsMade = [requestTime for requestTime in requestsMade if requestTime > datetime.datetime.now() - datetime.timedelta(seconds=1)]

    # Return whether we've made more requests in the last second, than the rate limit
    return len(requestsMade) > rate_limit


def fetch_pubmed(pmid, batch_size, parameters, requestsMade):
    # modified from: https://github.com/gijswobben/pymed/blob/master/pymed/api.py#L22
    parameters = parameters.copy()
    parameters["id"] = pmid
    # Make sure the rate limit is not exceeded
    while exceeded_rate_limit(requestsMade):
        pass
    try:
        # Make the request to PubMed
        response = requests.get(fetch_url, params=parameters)
    except ChunkedEncodingError:
        print('incomplete read, try again')
        time.sleep(1)
        response = requests.get(fetch_url, params=parameters)
    except HTTPError: 
        print('bad request, try again')
        time.sleep(1)
        response = requests.get(fetch_url, params=parameters)
    except ConnectionError:
        print('timed out, try again')
        time.sleep(1)
        response = requests.get(fetch_url, params=parameters)
    return response.content



def parse_pubmed_web_tree(tree):
    """
    Modified from https://github.com/titipata/pubmed_parser/blob/master/pubmed_parser/pubmed_web_parser.py
    Giving a tree Element from eutils, return parsed dictionary from the tree
    """
    title_elm = tree.xpath(".//articletitle")
    if len(title_elm) != 0:
        title = " ".join([title.text for title in title_elm if title is not None])
    else:
        title = ""

    abstract_tree = tree.xpath(".//abstract/abstracttext")
    abstract = " ".join([a.text.strip() for a in abstract_tree if a is not None])


    title_elm = tree.xpath(".//article//title")
    if len(title_elm) != 0:
        journal = ";".join([t.text.strip() for t in title_elm])
    else:
        journal = ""

    pubdate = tree.xpath('.//pubmeddata//history//pubmedpubdate[@pubstatus="medline"]')
    if len(pubdate) >= 1 and pubdate[0].find("year") is not None:
        year = pubdate[0].find("year").text
    else:
        year = ""

    affiliations = list()
    aff_elm = tree.xpath(".//affiliationinfo/affiliation")
    if aff_elm is not None:
        for affil in aff_elm:
            affiliations.append(affil.text)
    affiliations_text = "; ".join(affiliations)

    authors_tree = tree.xpath(".//authorlist/author")
    authors = list()
    if authors_tree is not None:
        for a in authors_tree:
            firstname = (
                a.find("forename").text if a.find("forename") is not None else ""
            )
            lastname = a.find("lastname").text if a.find("forename") is not None else ""
            fullname = (firstname + " " + lastname).strip()
            if fullname == "":
                fullname = (
                    a.find("collectivename").text
                    if a.find("collectivename") is not None
                    else ""
                )
            authors.append(fullname)
        authors_text = "; ".join(authors)
    else:
        authors_text = ""

    keywords = ""
    keywords_mesh = tree.xpath(".//meshheadinglist//meshheading")
    keywords_book = tree.xpath(".//keywordlist//keyword")
    if len(keywords_mesh) > 0:
        mesh_terms_list = []
        for m in keywords_mesh:
            keyword = (
                m.find("descriptorname").attrib.get("ui", "")
                + ":"
                + m.find("descriptorname").text
            )
            mesh_terms_list.append(keyword)
        keywords = ";".join(mesh_terms_list)
    elif len(keywords_book) > 0:
        keywords = ";".join([m.text or "" for m in keywords_book])
    else:
        keywords = ""

    doi = ""
    article_ids = tree.xpath(".//articleidlist//articleid")
    if len(article_ids) >= 1:
        for article_id in article_ids:
            if article_id.attrib.get("idtype") == "doi":
                doi = article_id.text

    dict_out = {
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "affiliation": affiliations_text,
        "authors": authors_text,
        "keywords": keywords,
        "doi": doi,
        "year": year,
    }
    return dict_out


def parse_xml(xml_tree):
    try:
        dict_out = parse_pubmed_web_tree(xml_tree)
        return dict_out
    except (TypeError, AttributeError):
        print('failed parse')


if __name__ == "__main__":
    """
    Fetch pubmed xmls from neuro pmids and parse using pubmed_parser
    """
    parser = argparse.ArgumentParser(description='Fetch pubmed xmls from neuro '
                                     'pmids and parse using pubmed_parser')
    parser.add_argument('-p', '--pmid_list',
                        help='Path to .txt file containing pmids',
                        required=True,
                        type=str)
    parser.add_argument('-e', '--pubmed_email',
                        help='pubmed email for communicating with Pubmed server',
                        required=True,
                        type=str)
    parser.add_argument('-b', '--batch_size',
                        help='batch size for fetching pubmed xml',
                        default=250,
                        required=False,
                        type=int)
    parser.add_argument('-n', '--n_processes',
                        help='number of processes in parallel pool',
                        default=8,
                        required=False,
                        type=int)
    args_dict = vars(parser.parse_args())

    # batch size 
    batch_size=args_dict['batch_size']

    # load pmids
    with open(args_dict['pmid_list'], 'r') as file:
        pmids = [line.rstrip() for line in file]

    # parameters to pass to pubmed server
    fetch_parameters = {
        "tool": 'fetch_pubmed', 
        "email": args_dict['pubmed_email'], 
        "db": "pubmed",
        'retmode': 'xml'
    }
    ncbi_api_key = os.getenv('NCBI_API_KEY')
    if ncbi_api_key is not None:
        fetch_parameters['api_key'] = ncbi_api_key
    # keep track of rate limit
    requestsMade = []
    # loop through batches and parse with pubmed web parser
    article_dicts = []
    article_indx = 0
    while article_indx < len(pmids):
        # fetch batch of articles from pmids
        pmid_batch = [int(float(p)) for p in pmids[article_indx:(article_indx+batch_size)]]
        try:
            xml_str = fetch_pubmed(pmid_batch, batch_size, fetch_parameters, requestsMade)
            requestsMade.append(datetime.datetime.now())
        except (ChunkedEncodingError, HTTPError, ConnectionError):
            print('failed twice, running fetch again')
            time.sleep(1)
            xml_str = fetch_pubmed(pmid_batch, batch_size, fetch_parameters, requestsMade)
            requestsMade.append(datetime.datetime.now())

        # create parallel pool
        pool = Pool(processes=args_dict['n_processes'])

        # split into separate articles
        xml_articles = html.fromstring(xml_str)
        xml_iter = xml_articles.iter('pubmedarticle')
        for article in pool.imap_unordered(func=parse_xml, iterable=xml_iter):
            if article is not None:
                article_dicts.append(article)

        article_indx+= batch_size
        print(f'articles parsed: {article_indx}')

    # write to json
    json.dump(article_dicts, open(f'pubmed_neuro_articles.json', 'w'), indent=4)

    