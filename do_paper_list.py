import os
import time
from pylatexenc.latexencode import utf8tolatex
import ads

# based and adapted from a code from Michael Mommert:
# https://mommermi.github.io/software/2019/01/27/generating-latex-publication-lists-from-nasa-ads.html


def query_papers(author, refereed=None, years=None, rows=1000):
    """query papers from NASA ADS

    :param author: str, author name
    :param refereed: boolean or `None`, if `True`, only extract refereed
                     publications; if `False`, only extract not refereed
                     publications; if `None`, extract all; default: `None`
    :param years: tuple, list, or `None`, range of years to query or `None`,
                  default: `None`
    :param rows: int, maximum number of publications to extract

    :return: list of ads publication objects
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
    papers = ads.SearchQuery(
        author=author,
        fq=fq,
        q=q,
        sort='pubdate',
        rows=rows,
        fl=['title', 'author', 'year', 'volume', 'page', 'pub', 'identifier', 'citation', 'doi', 'keyword', 'abstract'])
    return list(papers)


def create_paper_latex_line(paper, name=None, Number_authors_displayed=3):
    """create the latex document in strings using latex encoding

    :param paper: ads publication object
    :param name: string or `None`, name that will be highlighted in latex,
                 default: `None`
    param Number_authors_displayed: the number of authors displayed in the citation line
                                    also used to defined what is an "major paper" if
                                    the authors is in the first Number_authors_displayed authors

    :return: str, latex encoded string for paper
    """
    out = ''
    # put paper title in italic font
    title = ' ' + utf8tolatex(paper.title[0]) + ''

    # build author list
    if name is None:
        # treat all author names equally and list all of them
        authors = [utf8tolatex(paper.author[i]) for i in range(len(paper.author))]
        etal = False
    else:
        # highlight `name` in output string, if provided
        authors = []
        # name_found = False
        # dotdotdot = False
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
                name_short = author_name.split(', ')[0]
                # if name_short in author:
                #     authors.append('{\\bf ' + author + '}')
                # else:
                #     authors.append(author)
                authors.append(author)

                #if len(prenoms.split(' ')) > 2:
                #    print(author.split(' ')[1])
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
            authors = ' & '.join(authors)

    year = paper.year

    # create string with journal volume and page number
    pub = str(paper.pub)
    if paper.volume is not None:
        pub += ', ' + str(paper.volume)
    if paper.page is not None:
        pub += ', ' + str(paper.page[0])

    doi_link = ''
    # if paper.doi is not None:
    # print(paper.doi[0])
    # doi_link = ("\\url{http://doi.org/" + paper.doi[0] +"}")
    # doi_link = ('\href{https://doi.org/' + paper.doi[0] + '}{doi.org/' + paper.doi[0] + '}')
    # doi_link = ('\href{https://doi.org/' + paper.doi[0] + '}{DOI Link}')

    arxiv_link = ''
    # for ident in paper.identifier:
    #     if 'ArXiv:' in ident:
    #         arxiv_id = ident[6:]
    #         arxiv_link = ('\href{https://arxiv.org/abs/' + arxiv_id + '}{arxiv}')
    #     elif len(ident) == 10 and ident[4] == '.':
    #         arxiv_link = ('\href{https://arxiv.org/abs/' + ident + '}{arxiv}')

    # assemble output string as latex bullet list item
    out = ('- ' + authors + ' (' + year + '), ' + title + ', ' + pub)
    if doi_link != '':
        out += ', ' + doi_link
    if arxiv_link != '':
        out += ', ' + arxiv_link

    # add number of citations, if available
    if paper.citation is not None and len(paper.citation) > 1:
        out += ', ' + str(len(paper.citation)) + ' citations'
    elif paper.citation is not None and len(paper.citation) == 1:
        out += ', ' + str(len(paper.citation)) + ' citation'

    return out


def reject_cit(latex_string, reject_kw=None):
    """reject some citation substrings base on keywords

    reject_kw: string list of keywords
    param out: string containing publication information

    return latex_string: string
    """

    if reject_kw is None:  # no rejection everything goes
        return latex_string

    for s in reject_kw:
        if s in latex_string:
            return ''

    return latex_string


def select_cit(latex_string, select_kw=None):
    """reject some citation substrings base on keywords

    reject_kw: string list of keywords
    param out: string containing publication information

    return latex_string: string
    """

    if select_kw is None:  # no selection everything goes
        return latex_string

    for s in select_kw:
        if s in latex_string:
            return latex_string

    return ''


def clean_string(latex_string):
    """fix some citation substrings which is rejected by latex

    :param out: string containing publication information

    :return out: string
    """
    # substrings to be replaced
    fix = {
        '{\ensuremath{<}}SUB{\ensuremath{>}}': '',
        '{\ensuremath{<}}/SUB{\ensuremath{>}}': '',
        '<SUB>': '',
        '</SUB>': '',
        '─': '-',
        '': '',
        '\ensuremath': '',
        "{\'e}": 'é',
        "{\^e}": 'ê',
        "{\`e}": 'è',
        "{\'E}": 'É',
        "{\^a}": "â"
    }
    for key, val in fix.items():
        if key in latex_string:
            latex_string = latex_string.replace(key, val)

    # latex_string = latex_string.replace('#', '\#')
    # latex_string = latex_string.replace('&', '\&')
    # latex_string = latex_string.replace('{\'e}', 'é')
    # latex_string = latex_string.replace('{\'E}', 'É')

    return latex_string


def major_or_minor(latex_string, major=None):
    """sort major and minor publications
    
    :param latex_string: string containing publication information
    param major:    if None, take all
                    if True, only take the one where the author is in the first names
                    if True, only take the one where the author is NOT in the first names

    :return latex_string: string
    """
    name_short = author_name.split(', ')[0]
    if major is None:
        return latex_string
    elif major:
        if not name_short in latex_string:
            return ''
    elif not major:
        if name_short in latex_string:
            return ''

    return latex_string


def create_paper_list(author_name,
                      years,
                      Name_part='MY PAPERS',
                      refereed=None,
                      major=None,
                      reject_kw=None,
                      select_kw=None,
                      bullet='itemize'):
    """create a altex string for each subparts of the list

    :param out: string containing publication information

    :return out: latex string of a subpart
    """

    # latex_subpart = ''

    paper_str_list = list()
    year_list = list()

    # if you want to add recently accepted / submitted papers, you can do it here
    # for exampleyou can run without exluding 'arXiv e-prints', take the ones you are interested in the tex files
    # add them here and then run again excluding 'arXiv e-prints'
    # you can use \item[$\\bullet$] to avoid numbering them if they are not eccepted yet

    # pull references from ads
    papers = query_papers(author_name, refereed=refereed, years=years)

    there_at_least_one_cit = False

    for paper in list(papers):
        if paper.abstract is None:
            continue

        kw_bool = False
        for keyword_in_abstract in keywords_in_abstract:
            if keyword_in_abstract in paper.abstract.lower():
                kw_bool = True

        if not kw_bool:
            continue

        ref = clean_string(
            select_cit(reject_cit(major_or_minor(create_paper_latex_line(
                paper, author_name, Number_authors_displayed=Number_authors_displayed),
                                                 major=major),
                                  reject_kw=reject_kw),
                       select_kw=select_kw))

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

    ads.config.token = 'x58IUp8AXJ7WzCZyj1Py9zc3liBKaIvRjIwodThV'  # your ADS token
    # author_name = 'Mazoyer,  Johan'  # last name, first name
    # years = (2017, 2023)  # years to be queried: (start year, end year). If None, all years (careful with old homonyms)
    french = False  # True French, False English. Default is false (English)
    Number_authors_displayed = 3
    keywords_in_abstract = ['exoplanet', "protoplanet", 'disk', 'companion']

    group_publication = list()
    group_year_publication = list()

    author_list = [
        "Mazoyer, Johan", "Boccaletti, Anthony", "Paumard, Thibaut", "Baudoz, Pierre", "Clénet, Yann",
        "Coudé du Foresto, Vincent", "Galicher, Raphaël", "Gendron, Éric", "Gratadour, Damien", "Huby, Elsa",
        "Kervella, Pierre", "Lacour, Sylvestre", "Lagrange, Anne-Marie", "Perrin, Guy", "Rousset, Gérard",
        "Vincent, Frédéric", "Glanc, Marie", "Montargès, Miguel"
    ]
    # author_list = [ "Boccaletti, Anthony" ,"Lagrange, Anne-Marie", "Baudoz, Pierre" , "Galicher, Raphaël" , "Huby, Elsa"]
    # author_list = ["Lagrange, Anne-Marie"]

    for author_name in author_list:
        if author_name in ['Mazoyer, Johan', "Lagrange, Anne-Marie"]:
            years = (2020, 2023)
        elif author_name in ["Montargès, Miguel"]:
            years = (2021, 2023)
        else:
            years = (2017, 2023)

        list_auth, year_list = create_paper_list(
            author_name,
            refereed=True,
            years=years,
            major=True,
            # reject_kw=reject_kw_papers,
            bullet='enumerate')

        group_publication.extend(list_auth)
        group_year_publication.extend(year_list)

    group_publication_order = [x for _, x in sorted(zip(group_year_publication, group_publication))]

    group_publication_order_uniq = []
    for item in group_publication_order:
        if item not in group_publication_order_uniq:
            group_publication_order_uniq.append(item)

    for i in group_publication_order_uniq:
        print(i)
        print("")
    print(len(group_publication_order_uniq))