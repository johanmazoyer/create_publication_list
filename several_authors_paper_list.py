import ads
from create_publist import *
import pandas as pd


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
    title = '{\\it ' + utf8tolatex(paper.title[0]) + '}'

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
                             fl=['title', 'author', 'year', 'volume', 'page', 'pub', 'identifier', 'citation', 'doi',"abstract"])
    
    return list(papers)


def create_paper_list(researcher_name,
                         years,
                         Number_authors_displayed=3,
                         refereed=None):
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

        if paper.abstract is None:
                continue

        kw_bool = False
        for keyword_in_abstract in keywords_in_abstract:
            if keyword_in_abstract in paper.abstract.lower():
                kw_bool = True

        if not kw_bool:
            continue

        ref = clean_string(major_or_minor(researcher_name,create_paper_latex_line_bis(
                paper, researcher_name, Number_authors_displayed=Number_authors_displayed),major=True))

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
    ads.config.token = config["ads_config_token"]  # your ADS token

    check_ads_token()
    range_years = (2019, 2023)  # years to be queried: (start year, end year). If None, all years (careful with old homonyms)
    french = False  # True French, False English. Default is false (English)
    Number_authors_displayed = 3
    keywords_in_abstract = ['exoplanet', "protoplanet", 'disk', 'companion', 'protoplanetary']

    group_publication = list()
    group_year_publication = list()

    list_authorscsv = pd.read_csv('/Users/jmazoyer/Desktop/Liste_names_exoplanet.csv', header=1)

    author_list = list()
    for ind in list_authorscsv.index:
        author_list.append(list_authorscsv["nom"][ind].strip() + ", " + list_authorscsv["prenom"][ind].strip())


    # author_list = [
    #     "Mazoyer, Johan", "Boccaletti, Anthony", "Paumard, Thibaut", "Baudoz, Pierre", "Clénet, Yann",
    #     "Coudé du Foresto, Vincent", "Galicher, Raphaël", "Gendron, Éric", "Gratadour, Damien", "Huby, Elsa",
    #     "Kervella, Pierre", "Lacour, Sylvestre", "Lagrange, Anne-Marie", "Perrin, Guy", "Rousset, Gérard",
    #     "Vincent, Frédéric", "Glanc, Marie", "Montargès, Miguel"
    # ]
    # author_list = [ "Boccaletti, Anthony" ,"Lagrange, Anne-Marie", "Baudoz, Pierre" , "Galicher, Raphaël" , "Huby, Elsa"]

    for author_name in author_list:
        print(author_name)

        list_auth, year_list = create_paper_list(
            author_name,
            range_years,
            refereed = True)

        group_publication.extend(list_auth)
        group_year_publication.extend(year_list)

    group_publication_order = [x for _, x in sorted(zip(group_year_publication, group_publication))]

    group_publication_order_uniq = []
    for item in group_publication_order:
        if item not in group_publication_order_uniq:
            group_publication_order_uniq.append(item)

    # for i in group_publication_order_uniq:
    #     print(i)
    #     print("")
    # print(len(group_publication_order_uniq))

    with open('/Users/jmazoyer/Desktop/Liste_papiers_exoplanet.txt', 'w') as f:
        for i in group_publication_order_uniq:
            f.write(i  + '\n')
            f.write('\n')