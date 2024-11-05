# “The Brain is…”: A Survey of The Brain’s Many Definitions
This repository contains the code to produce the results of the manuscript _'The Brain is...': A Survey of the Brain's Many Definitions_ to be published in _Neuroinformatics_
 (forthcoming). The repository contains a series of commandline Python scripts to: 
   1) Extract articles containing entity terms (e.g. 'brain', 'heart', 'lungs' - `entity_strings.txt`) from the corpus of full-text articles (in .xml format) in the Pubmed Central (PMC) Articles Dataset using `find_pubmed_articles.py`.
   2) Extract phrase of the expression _'The/a _____ is/are a/the ...'_, where the placeholder is an organ (e.g. 'brain' ,'heart', 'lungs'), from the extracted articles in PMC Articles Dataset using `parse_sentence.py`. In addition, a corpus of abstracts from prominent neuroscience journals was included in this extraction to improve representation of the scientific literature outside of the PMC Articles Dataset. A list of PubMed reference numbers (PMID) for the article abstracts are provided in `data/neuro_abstract_pmid.txt`. You can download these abstracts using the EFetch utility in `fetch_pubmed_neuro_abstracts.py`. 
   3) Embed the artices into a vector space for further analysis using `embed_sentence.py`.

For all commandline scripts input parameters are documented and can be printed to the commandline using `python script.py -h`.

If you would like to start from the extracted phrases from the full corpus (the output of step 2 above), including the PMC Articles dataset and neuroscience journal abstracts, you will find those provided in `data/matched_expressions.txt`.

The figures and main results of the manuscript are contained in the Jupyter notebook `the_brain_is.ipynb`. Note, you must have run the commandline scripts above (or step 3, starting with `matched_expressions.txt) to successfully run the code in the notebook.

# PMC Articles Dataset
The PMC Articles Dataset (https://pmc.ncbi.nlm.nih.gov/tools/textmining/) contains full-text scientific articles in machine-readable formats (e.g. .xml). The datasets used in this study were the _PMC Open Access Subset Dataset_ and _Author Manuscript Dataset_. The easiest way to get the full datasets is via bulk downloads using the PMC File Transfer Protocol (FTP) Service (https://pmc.ncbi.nlm.nih.gov/tools/ftp/). Individual article files are stored in tar archive files and must be 'unzipped' after downloading. Both the download and extraction/unzip will take quite a while. 








