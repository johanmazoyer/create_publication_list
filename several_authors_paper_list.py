import os
import numpy as np
import ads
from pylatexenc.latexencode import utf8tolatex
from unidecode import unidecode
from create_publist import clean_string, major_or_minor, check_ads_token
import pandas as pd
import matplotlib.pyplot as plt
import yaml
import csv
import random

all_papers = list()


def create_paper_latex_line_bis(paper, researcher_name=None, Number_authors_displayed=3):
    """From a paper, create a string line in latex format.

    Parameters
    ----------
    paper: ads publication object
    researcher_name: string or `None`, name that will be highlighted in latex,
                    default: `None`
    Number_authors_displayed: the number of authors displayed in the citation line
                                    also used to defined what is an "major paper" if
                                    the authors is in the first Number_authors_displayed authors

    Returns
    ------------
    str, latex encoded string for paper
    """
    out = ''
    # put paper title in italic font

    title_uncleaned = paper.title[0]
    title_uncleaned.replace("★", "*")

    title = '{\\it ' + utf8tolatex(title_uncleaned, substitute_bad_chars=True) + '}'

    # build author list

    authors = []

    etal = False
    comma_or_and_between_authors = 'coma'

    if len(paper.author) == 2:
        comma_or_and_between_authors = 'and'

    for i in range(len(paper.author)):
        # `name` is the i-th author on this paper
        author = utf8tolatex(paper.author[i])
        nom = author.split(',')[0]
        if len(author.split(',')) > 1:
            prenoms = author.split(',')[1]
        else:
            prenoms = '?'
        prenoms = prenoms.replace("-", " -")
        prenoms = prenoms.split(' ')
        while True:
            try:
                prenoms.remove('')
            except ValueError:
                break

        for prenomj, prenom in enumerate(prenoms):
            if prenom[0] == '-':
                prenoms[prenomj] = prenom[0:2] + '.'
            elif prenom[0] == '{':
                end = prenom.find('}')
                prenoms[prenomj] = prenom[0:end + 1] + '.'
            else:
                prenoms[prenomj] = prenom[0] + '.'

        author = nom + ", " + " ".join(prenoms)
        #print(author)

        if i < Number_authors_displayed:
            authors.append(author)
        else:
            etal = True
            break

    # join author list and add 'et al.' if required
    if etal:
        authors = ' ; '.join(authors) + ' et al.'
    else:
        if comma_or_and_between_authors == 'coma':
            authors = ' ; '.join(authors)
        else:
            authors = ' \\altand~'.join(authors)

    year = paper.year

    # create string with journal volume and page number
    pub = str(paper.pub)
    if paper.volume is not None:
        pub += ', ' + str(paper.volume)
    if paper.page is not None:
        pub += ', ' + str(paper.page[0])

    doi_link = ''
    if paper.doi is not None:
        doi_link = ('\href{https://doi.org/' + paper.doi[0] + '}{DOI Link}')

    arxiv_link = ''
    for ident in paper.identifier:
        if 'ArXiv:' in ident:
            arxiv_id = ident[6:]
            arxiv_link = ('\href{https://arxiv.org/abs/' + arxiv_id + '}{arxiv}')
        elif len(ident) == 10 and ident[4] == '.':
            arxiv_link = ('\href{https://arxiv.org/abs/' + ident + '}{arxiv}')

    # assemble output string as latex bullet list item
    out = ('\\item ' + authors + ' (' + year + '), ' + title + ', ' + pub)
    if doi_link != '':
        out += ', ' + doi_link
    elif arxiv_link != '':
        out += ', ' + arxiv_link

    # add number of citations, if available
    if paper.citation is not None and len(paper.citation) > 1:
        out += ', ' + str(len(paper.citation)) + ' citations'
    elif paper.citation is not None and len(paper.citation) == 1:
        out += ', ' + str(len(paper.citation)) + ' citation'

    return out


def query_papers_with_abstract(author, refereed=None, years=None, rows=1000):
    """query papers from NASA ADS

    Parameters
    ----------
    author: str, author name
    refereed: boolean or `None`, if `True`, only extract refereed
                     publications; if `False`, only extract not refereed
                     publications; if `None`, extract all; default: `None`
    years: tuple, list, or `None`, range of years to query or `None`,
                  default: `None`
    rows: int, maximum number of publications to extract

    Returns
    ------------
    list of ads publication objects
    """
    # set query payload
    if refereed is None:
        q = ''
    elif refereed:
        q = 'property:refereed'
    elif not refereed:
        q = 'property:notrefereed'
    fq = 'database:(physics OR astronomy)'
    if years is not None:
        fq += " year:{0}-{1}".format(years[0], years[1])

    # perform query
    papers = ads.SearchQuery(author=author,
                             fq=fq,
                             q=q,
                             sort='pubdate',
                             rows=rows,
                             fl=[
                                 'title', 'author', 'year', 'volume', 'page', 'pub', 'identifier', 'citation', 'doi',
                                 'abstract', 'grant', 'aff', "bibcode"
                             ])

    return list(papers)


def create_paper_list(researcher_name, years, Number_authors_displayed=3, refereed=None):
    """Create a Latex paragraph with a paper list based on different options

    Parameters
    ----------
    researcher_name : string, name of the reserachers for which this list is created
    years: tupple, range of years in the query
    Name_part: string, optional, default 'MY PAPERS'
                name of the latex subpart
    Number_authors_displayed: int, optinal, default = 3
                number of author printed by paper. This is also the criteria used to distinguished if a paper is 'major' or 'minor'
    refereed: 'True', 'False' or 'None'
            If True, only refereed papers are listed in this latex subpart, 
            If False, only non refereed papers are listed in this latex subpart, 
            if None, all papers are listed in this latex subpart, 
    major: 
            If True, only major papers strings are listed in this latex subpart (if researcher_name position in the author list <= Number_authors_displayed), 
            If False, only minor papers strings are listed in this latex subpart (if researcher_name position in the author list > Number_authors_displayed), 
            if None, all paper strings are returned
    reject_kw: list of string or None
            a list of keywords that can be used to reject some papers. Example reject_kw=['arXiv e-prints']
    select_kw: list of string or None
            a list of keywords that can be used to select only some papers. Example select_kw=['Thesis']
    bullet: string
        latex list option 'enumerate' or 'itemize'
    add_publi_manually: list
        add publication to this list no matter what. This can be for example a publication submitted but not yet on ADS. the format must be a list
        where each elements is a list of 2 element. The first one is 'last' (paper will be injected at the latest of the list) or 'year', paper will be injected at a specific year
        and the second oen is the latex string of the paper. See yaml file for help

    Returns
    ------------
    latex_paragraph: string, paragraph in the latex 
    """

    paper_str_list = list()
    year_list = list()

    # pull references from ads
    papers = query_papers_with_abstract(researcher_name, refereed=refereed, years=years)
    there_at_least_one_cit = False

    for paper in papers:

        # print(paper.author[0], paper.title)

        kw_bool = False
        for keyword_in_abstract in keywords_in_abstract:
            if keyword_in_abstract in paper.title[0].lower():
                kw_bool = True

        if paper.abstract is None:
            # print("no abstract")
            continue

        for keyword_in_abstract in keywords_in_abstract:
            if keyword_in_abstract in paper.abstract.lower():
                kw_bool = True

        # print(kw_bool)
        # print("")

        if not kw_bool:
            continue

        all_papers.append(paper)

        ref = clean_string(
            major_or_minor(researcher_name,
                           create_paper_latex_line_bis(paper,
                                                       researcher_name,
                                                       Number_authors_displayed=Number_authors_displayed),
                           major=True))

        if len(ref) > 0:
            there_at_least_one_cit = True

            # print(paper.author[0], paper.year)
            year_here = paper.year
            paper_str_list.append(ref)
            year_list.append(year_here)

            # latex_subpart = latex_subpart + ref + '\n\n'

    if not there_at_least_one_cit:
        return list(), list()

    # latex_subpart = latex_subpart + '\\end{' + bullet + '}\n\n'
    # print(paper_str_list)
    return paper_str_list, year_list


if __name__ == '__main__':

    with open(os.path.join(os.getcwd(), 'config_pub_list_maz.yaml'), 'r') as file:
        config = yaml.safe_load(file)
    # first get a token https://ads.harvard.edu/handouts/ADS_API_handout.pdf
    ads.config.token = config["ads_config_token"]  # replace by your ADS token

    check_ads_token()
    range_years = (2019, 2023
                  )  # years to be queried: (start year, end year). If None, all years (careful with old homonyms)
    french = False  # True French, False English. Default is false (English)
    Number_authors_displayed = 5
    keywords_in_abstract = ['exoplanet', 'rocky planets', 'jupiters', 'protoplanet', 'debris', 'companion', 'exocomet']

    group_publication = list()
    group_year_publication = list()

    list_authorscsv = pd.read_csv('/Users/jmazoyer/Desktop/papers_exoplanets/Liste_names_exoplanet3.csv', header=1)

    author_list = list()
    for ind in list_authorscsv.index:
        author_list.append(list_authorscsv["nom"][ind].strip().lower().capitalize() + ", " +
                           list_authorscsv["prenom"][ind].strip().lower().capitalize())

    author_list.sort()

    # indices_here = random.sample(range(0, 175), 20)
    # author_list = [author_list[i] for i in indices_here]

    # author_list = ["Fouqué, Pascal"]

    for author_name in author_list:
        print(author_name)

        list_auth, year_list = create_paper_list(author_name,
                                                 range_years,
                                                 Number_authors_displayed=Number_authors_displayed,
                                                 refereed=True)

        group_publication.extend(list_auth)
        group_year_publication.extend(year_list)

    group_publication_order = [x for _, x in sorted(zip(group_year_publication, group_publication))]

    group_publication_order_uniq = []
    for item in group_publication_order:
        if item not in group_publication_order_uniq:
            group_publication_order_uniq.append(item)

    with open('/Users/jmazoyer/Desktop/papers_exoplanets/Liste_papiers_exoplanet.txt', 'w') as f:
        for i in group_publication_order_uniq:
            f.write(i + '\n')
            f.write('\n')

    # for i in group_publication_order_uniq:
    #     print(i)
    #     print("")
    # print(len(group_publication_order_uniq))

    ############################################
    ## Extract affiliation
    ###########################################
    paper_uniq = []
    for paperi in all_papers:
        if paperi not in paper_uniq:
            paper_uniq.append(paperi)

    # print(len(all_papers), len(paper_uniq))
    total_apper_with_french_Afil = 0

    french_afil_Acro_allpaper = list()

    info_papers = dict()
    info_papers["year"] = list()
    info_papers["afil_acro"] = list()
    info_papers["title"] = list()
    info_papers["first_auth"] = list()

    # french_afil_Acro_allpaper_peryear = dict()

    year_allpaper = list()

    for toto, paper in enumerate(paper_uniq):

        french_afil = list()
        for afil in paper.aff:
            if "france" in afil.lower():
                french_afil.append(afil)

        if len(french_afil) > 0:
            total_apper_with_french_Afil += 1
            year_allpaper.append(paper.year)
        else:
            continue

        french_afil_Acro_this_paper = list()

        for afil_i in french_afil:

            afil_i = afil_i.lower()
            afil_i = unidecode(afil_i).replace("'", "").replace("-", " ").replace("`", "")
            afil_i = afil_i.replace("d astrophysique", "dastrophysique")

            not_found_any_afil = True
            if any(laboname in afil_i for laboname in ["onera"]):
                french_afil_Acro_this_paper.append("ONERA")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["lesia", "laboratoire detudes spatiales et dinstrumentation en astrophysique"]):
                french_afil_Acro_this_paper.append("LESIA")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["laboratoire de physique et chimie de lenvironnement et de lespace", "lpc2e"]):
                french_afil_Acro_this_paper.append("LPC2E")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire de physique de lens"]):
                french_afil_Acro_this_paper.append("Laboratoire de Physique de l'ENS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "ipag", "institut de planetologie et dastrophysique de grenoble",
                    "institute of planetology and astrophysics of grenoble", "laboratoire dastrophysique de grenoble",
                    "institut de planetologie et astrophysique de grenoble"
                    "institut de planetologie et dastrophysique, university of grenoble",
                    "institut de planetologie et astrophysique, de grenoble"
            ]):
                french_afil_Acro_this_paper.append("IPAG")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in
                   ["cral", "centre de recherche astrophysique de lyon", "centre de recherche astrophysique, de lyon"]):
                french_afil_Acro_this_paper.append("CRAL")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["observatoire astronomique de strasbourg"]):
                french_afil_Acro_this_paper.append("ObAS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["lagrange"]):
                french_afil_Acro_this_paper.append("Lagrange")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut fresnel"]):
                french_afil_Acro_this_paper.append("Institut Fresnel")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "iap", "institut dastrophysique de paris", "institute dastrophysique de paris",
                    "institut dastrophysique de pari s"
            ]):
                french_afil_Acro_this_paper.append("IAP")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["lam,", "laboratoire dastrophysique de marseille"]):
                french_afil_Acro_this_paper.append("LAM")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["lmd", "laboratoire de meteorologie dynamique", "lab. de meteorologie dynamique"]):
                french_afil_Acro_this_paper.append("LMD")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["ias, ", "institut dastrophysique spatiale"]):
                french_afil_Acro_this_paper.append("IAS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["observatoire de haute provence"]):
                french_afil_Acro_this_paper.append("OHP")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in
                   ["lab,", "laboratoire dastrophysique de bordeaux", "laboratory of astrophysics at bordeaux"]):
                french_afil_Acro_this_paper.append("LAB")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in
                   ["lerma", "laboratoire detudes du rayonnement et de la matiere en astrophysique et atmospheres"]):
                french_afil_Acro_this_paper.append("LERMA")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["irap", "institut de recherche en astrophysique et planetologie"]):
                french_afil_Acro_this_paper.append("IRAP")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["laboratoire interuniversitaire des systemes atmospheriques", "lisa"]):
                french_afil_Acro_this_paper.append("LISA")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["piim", "physique des interactions ioniques et moleculaires"]):
                french_afil_Acro_this_paper.append("PIIM")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "ipgp", "institut de physique du globe de paris", "institut de physique du globe",
                    "paris globe institute of physics"
            ]):
                french_afil_Acro_this_paper.append("IPGP")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["imcce", "imcee", "institut de mecanique celeste et de calcul des ephemerides"]):
                french_afil_Acro_this_paper.append("IMCCE")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut doptique graduate school"]):
                french_afil_Acro_this_paper.append("IOGS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire univers et theories", "luth"]):
                french_afil_Acro_this_paper.append("LUTH")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut de radioastronomie millimetrique", "iram"]):
                french_afil_Acro_this_paper.append("IRAM")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["maison de la simulation", "house of simulation"]):
                french_afil_Acro_this_paper.append("MdlS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in
                   ["irfu", "laboratoire aim", "aim,", "astrophysique, instrumentation et modelisation"]):
                french_afil_Acro_this_paper.append("IRFU")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire dannecy le vieux de physique theorique", "lapth"]):
                french_afil_Acro_this_paper.append("LAPTh")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "utinam",
                    "univers, temps-frequence, interfaces, nanostructures, atmosphere et environnement, molecules"
            ]):
                french_afil_Acro_this_paper.append("UTINAM")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire univers et particules de montpellier", "lupm"]):
                french_afil_Acro_this_paper.append("LUPM")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "institut superieur de laeronautique et de lespace", "institut superieur en aeronautique et espace",
                    "isae"
            ]):
                french_afil_Acro_this_paper.append("ISAE")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["canada-france-hawaii telescope", "cfht"]):
                french_afil_Acro_this_paper.append("CFHT")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire de planetologie de nantes"]):
                french_afil_Acro_this_paper.append("Laboratoire de planétologie de Nantes")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["crpg", "centre de recherches petrographiques et geochimiques"]):
                french_afil_Acro_this_paper.append("CRPG")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["gepi", "galaxies, etoiles, physique et instrumentation"]):
                french_afil_Acro_this_paper.append("GEPI")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["lgl", "umr 5276"]):
                french_afil_Acro_this_paper.append("Laboratoire de Géologie de Lyon")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["syrte", "systemes de reference temps espace"]):
                french_afil_Acro_this_paper.append("SYRTE")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "latmos", "laboratoire atmospheres, observations spatiales",
                    "laboratoire atmospheres, milieux, observations spatiales",
                    "laboratoire atmospheres, milieux et observations spatiales"
            ]):
                french_afil_Acro_this_paper.append("LATMOS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut lumiere matiere"]):
                french_afil_Acro_this_paper.append("Institut Lumière Matière")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["canada france hawaii telescope", "cfht"]):
                french_afil_Acro_this_paper.append("CFHT")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire reactions et genie des procedes", "lrgp"]):
                french_afil_Acro_this_paper.append("LRGP")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire de planetologie et geosciences"]):
                french_afil_Acro_this_paper.append("Laboratoire de planétologie et Géosciences")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["geops", "geosciences paris saclay"]):
                french_afil_Acro_this_paper.append("GEOPS")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut des sciences moleculaires"]):
                french_afil_Acro_this_paper.append("Institut des Sciences Moléculaires")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["lapp", "laboratoire dannecy de physique des particules"]):
                french_afil_Acro_this_paper.append("LAPP")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "groupe de spectrometrie moleculaire et atmospherique",
                    "groupe de spectroscopie moleculaire et atmospherique", "gsma"
            ]):
                french_afil_Acro_this_paper.append("GSMA")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire de geologie de lyon"]):
                french_afil_Acro_this_paper.append("GSMA")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["laboratoire de planetologie et geodynamique"]):
                french_afil_Acro_this_paper.append("Laboratoire de Planetologie et Géodynamique")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut de chimie physique", "laboratoire de chimie physique"]):
                french_afil_Acro_this_paper.append("Institut de Chimie Physique")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "institut de mineralogie, de physique des materiaux et de cosmochimie",
                    "institut de mineralogie, physique des materiaux et cosmochimie", "impmc"
            ]):
                french_afil_Acro_this_paper.append("IMPMC")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["institut des sciences de la terre dorleans", "isto"]):
                french_afil_Acro_this_paper.append("ISTO")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in ["astroparticule et cosmologie"]):
                french_afil_Acro_this_paper.append("APC")
                not_found_any_afil = False

            if any(laboname in afil_i
                   for laboname in ["observatoire des baronnies provencales", "baronnies provencales observatory"]):
                french_afil_Acro_this_paper.append("Observatoire des Baronnies Provencales")
                not_found_any_afil = False

            if any(laboname in afil_i for laboname in [
                    "lab sticc", "agenium", "pixyl", "european space agency", "mesocentre de calcul de franche comte",
                    "mesocentre de franche comte", "silios", "thales", "laboratoire de physique des deux infinis",
                    "centre de biophysique moleculaire", "centre lasers intenses et applications",
                    "institut de mecanique des fluides de toulouse", "amateur astronomer 101"
            ]):
                french_afil_Acro_this_paper.append("Irrelevant")
                not_found_any_afil = False

            french_afil_Acro_this_paper = list(set(french_afil_Acro_this_paper))

            # if not_found_any_afil:
            #     print(afil_i)
        french_afil_Acro_allpaper += french_afil_Acro_this_paper

        info_papers["year"].append(paper.year)
        info_papers["afil_acro"].append(french_afil_Acro_this_paper)
        info_papers["title"].append(paper.title)
        info_papers["first_auth"].append(paper.author[0])

        # french_afil_Acro_allpaper_peryear[str(paper.year)] += french_afil_Acro_this_paper

        # print(toto, len(paper.aff), len(french_afil), len(french_afil_Acro_this_paper))

    # first to identify all institution papers
    keys, counts = np.unique(french_afil_Acro_allpaper, return_counts=True)
    # print(french_afil_Acro_allpaper)
    big_lab_keys = []
    big_lab_counts = []
    for i in range(len(keys)):
        print(keys[i], counts[i])
        if counts[i] > 25 and keys[i] != "Irrelevant":
            big_lab_counts.append(counts[i])
            big_lab_keys.append(keys[i])

    plt.bar(big_lab_keys, big_lab_counts)
    plt.ylim(0, 100 * (np.ceil(max(big_lab_counts) * 1.2 / 100)))

    plt.xticks(rotation=30, ha='right')
    plt.title(f"Publications 'exoplanètes' françaises par laboratoire (2019-2023)")
    plt.text(-0.5, max(big_lab_counts) * 1.18, "Attention, une même publication est ici comptée plusieurs fois si")
    plt.text(-0.5, max(big_lab_counts) * 1.12, "elle inclue des auteurs dans différents laboratoires français.")
    plt.text(-0.5, max(big_lab_counts) * 1.06, f"Le nombre de publications réel est de {total_apper_with_french_Afil}.")

    plt.ylabel('Nombre de publications')

    plt.savefig("/Users/jmazoyer/Desktop/papers_exoplanets/publi_par_labo.pdf")

    ######## print in csv

    # for i in range(len(info_papers["year"])):
    #     afil_acro = info_papers["afil_acro"][i]
    #     check_publilabo = "LESIA"
    #     if check_publilabo in afil_acro:
    #         print(f"{check_publilabo} {info_papers['year'][i]}: {info_papers['first_auth'][i]} , {info_papers['title'][i]}")

    french_afil_Acro_allpaper_peryear = dict()
    french_afil_Acro_allpaper_peryear["2023"] = list()
    french_afil_Acro_allpaper_peryear["2022"] = list()
    french_afil_Acro_allpaper_peryear["2021"] = list()
    french_afil_Acro_allpaper_peryear["2020"] = list()
    french_afil_Acro_allpaper_peryear["2019"] = list()

    for i, year in enumerate(info_papers["year"]):
        french_afil_Acro_allpaper_peryear[str(year)] += info_papers['afil_acro'][i]

    keys2023, counts2023 = np.unique(french_afil_Acro_allpaper_peryear['2023'], return_counts=True)
    keys2022, counts2022 = np.unique(french_afil_Acro_allpaper_peryear['2022'], return_counts=True)
    keys2021, counts2021 = np.unique(french_afil_Acro_allpaper_peryear['2021'], return_counts=True)
    keys2020, counts2020 = np.unique(french_afil_Acro_allpaper_peryear['2020'], return_counts=True)
    keys2019, counts2019 = np.unique(french_afil_Acro_allpaper_peryear['2019'], return_counts=True)

    f = open('/Users/jmazoyer/Desktop/papers_exoplanets/publi_par_labo.csv', 'w')

    # create the csv writer
    writer = csv.writer(f)

    # write a row to the csv file
    writer.writerow(["labo", "2019", "2020", "2021", "2022", "2023"])

    for key in keys:
        if key == "Irrelevant":
            continue

        if key in keys2023:
            counthere2023 = counts2023[np.where(keys2023 == key)][0]
        else:
            counthere2023 = 0

        if key in keys2022:
            counthere2022 = counts2022[np.where(keys2022 == key)][0]
        else:
            counthere2022 = 0

        if key in keys2021:
            counthere2021 = counts2021[np.where(keys2021 == key)][0]
        else:
            counthere2021 = 0

        if key in keys2020:
            counthere2020 = counts2020[np.where(keys2020 == key)][0]
        else:
            counthere2020 = 0

        if key in keys2019:
            counthere2019 = counts2019[np.where(keys2019 == key)][0]
        else:
            counthere2019 = 0
        writer.writerow([key, counthere2019, counthere2020, counthere2021, counthere2022, counthere2023])

    # close the file
    f.close()

    ############################################
    ############################################
    ############################################
    ############################################

    listannee, countspubli_annee = np.unique(year_allpaper, return_counts=True)

    fig, ax = plt.subplots()
    rects1 = ax.bar(listannee, countspubli_annee)

    # plt.hist(listannee,len(listannee), weights=publi_annee)
    ax.set_xlabel('Année')
    ax.set_ylabel('Nombres de publications')
    ax.set_title(f"Publications 'exoplanètes' françaises (total = { total_apper_with_french_Afil })")

    plt.savefig("/Users/jmazoyer/Desktop/papers_exoplanets/paper_per_year.pdf")
