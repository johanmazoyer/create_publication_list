import os
import time
from pylatexenc.latexencode import utf8tolatex
import ads
import yaml

# based and adapted from a code from Michael Mommert:
# https://mommermi.github.io/software/2019/01/27/generating-latex-publication-lists-from-nasa-ads.html


def check_ads_token():
    """Check if the given token exist py trying to runa query
    """

    try:
        papers = list(ads.SearchQuery(q="exoplanets", sort="citation_count", rows=2))
    except:
        raise Exception(
            "you first need to create a ADS token, following this proceedure (it takes 10 seconds): https://ads.harvard.edu/handouts/ADS_API_handout.pdf"
        )


def measure_h_factor(author, refereed=None, years=None, rows=1000):
    """compute the researcher's h-index.

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
    h_factor : int, h factor of the researcher
    """

    papers = query_papers(author, refereed=refereed, years=years, rows=rows)

    citations = []
    for paper in papers:
        if paper.citation is not None:
            citations.append(len(paper.citation))
    return sum(x >= i + 1 for i, x in enumerate(sorted(citations, reverse=True)))


def query_papers(author, refereed=None, years=None, rows=1000):
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
                             fl=['title', 'author', 'year', 'volume', 'page', 'pub', 'identifier', 'citation', 'doi'])
    return list(papers)


def create_paper_latex_line(paper, researcher_name=None, Number_authors_displayed=3):
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
            researcher_name_short = researcher_name.split(', ')[0]
            if researcher_name_short in author:
                authors.append('{\\bf ' + author + '}')
            else:
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
    out = ('\\item ' + authors + ' ({\\bf' + year + '}), ' + title + ', ' + pub)
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


def reject_cit(latex_string, reject_kw=None):
    """Reject some paper latex paper lines based on some keywords.
        Example: you want to avoid certain publications.

    Parameters
    ----------
    latex_string: string, one paper line in the latex
    reject_kw: string, list of keywords. Optional, default None
                if None,  everything is returned

    Returns
    ------------
    latex_string: string, one paper line in the latex or ''
    """

    if reject_kw is None:  # no rejection everything goes
        return latex_string

    for s in reject_kw:
        if s in latex_string:
            return ''

    return latex_string


def select_cit(latex_string, select_kw=None):
    """Reject some paper latex paper lines unless they have certain keywords.
        Example: you only want Thesis

    Parameters
    ----------
    latex_string: string, one paper line in the latex
    select_kw: string, list of keywords. Optional, default None
                if None,  everything is returned

    Returns
    ------------
    latex_string: string, one paper line in the latex or ''

    """

    if select_kw is None:  # no selection everything goes
        return latex_string

    for s in select_kw:
        if s in latex_string:
            return latex_string

    return ''


def clean_string(latex_string):
    """Fix some citation substrings which is rejected by latex. This is a pain 
        in the back, people put weird stuff in their paper titles, you might need to modify this
        if you cannot compile your latex

    Parameters
    ----------
    latex_string: string, one paper line in the latex

    Returns
    ------------
    cleaned_latex_string: string, one paper line in the latex 

    """

    # substrings to be replaced
    fix = {
        '─': '-',
        '#': '\#',
        '{\\&}amp;': '\&',
        '&amp;': '\&',
        '&': '\&',
        '\\\\&': '\&',
        '★': 'star',
        '⨁': 'earth',
        '{\ensuremath{<}}SUB{\ensuremath{>}}': '$_{',
        '{\ensuremath{<}}SUP{\ensuremath{>}}': '$^{',
        '{\ensuremath{<}}/SUB{\ensuremath{>}}': '}$',
        '{\ensuremath{<}}/SUP{\ensuremath{>}}': '}$',
        '\\textdegree': 'degrees',
    }
    for key, val in fix.items():
        if key in latex_string:
            latex_string = latex_string.replace(key, val)

    return latex_string


def major_or_minor(researcher_name, latex_string, major=None):
    """Select major and minor publications based on if the reseracher name is in it,
        which depend if the Number_authors_displayed chosen.

    Parameters
    ----------
    researcher_name : string, name of the reserachers for which this list is created
    latex_string: string, one paper line in the latex
    major: 'True', 'False' or 'None'
            If True, only paper strings in which the resarchers name is listed are returned, 
            If False, only paper strings in which the resarchers name is NOT listed are returned, 
            if None, all paper strings are returned

    Returns
    ------------
    selected_latex_string: string, one paper line in the latex 

    """
    name_short = researcher_name.split(', ')[0]
    if major is None:
        return latex_string
    elif major:
        if not name_short in latex_string:
            return ''
    elif not major:
        if name_short in latex_string:
            return ''

    return latex_string


def create_latex_subpart(researcher_name,
                         years,
                         Name_part='MY PAPERS',
                         Number_authors_displayed=3,
                         refereed=None,
                         major=None,
                         reject_kw=None,
                         select_kw=None,
                         bullet='itemize',
                         add_publi_manually=list()):
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

    latex_subpart = ('\\vspace{-0.9cm}\n'
                     '\\textcolor{RoyalBlue}{\\section*{\large ' + Name_part + '}\n'
                     '\\vspace{-0.3cm}\hrule}\n'
                     '\\vspace{0.4cm}\n\n'
                     '\\begin{' + bullet + '} \itemsep -1pt\n\n')

    # pull references from ads
    papers = query_papers(researcher_name, refereed=refereed, years=years)
    there_at_least_one_cit = False

    publi_manu_years = list()
    for publi_manu in add_publi_manually:
        if publi_manu == []:
            continue
        if publi_manu[0] == 'last':
            there_at_least_one_cit = True
            latex_subpart += publi_manu[1] + '\n\n'
        else:
            try:
                year = int(publi_manu[0])
            except:
                print(publi_manu)
                raise Exception(("when adding a paper, add a 2 elements list: first one is the position",
                                 "where you want to insert it (year of 'last'), second one is the latex string line "))
            there_at_least_one_cit = True
            bool_is_injected = True
            publi_manu_years.append([year, publi_manu[1], bool_is_injected])

    for paper in list(papers):
        ref = clean_string(
            select_cit(reject_cit(major_or_minor(researcher_name,
                                                 create_paper_latex_line(
                                                     paper,
                                                     researcher_name,
                                                     Number_authors_displayed=Number_authors_displayed),
                                                 major=major),
                                  reject_kw=reject_kw),
                       select_kw=select_kw))

        if len(ref) > 0:
            there_at_least_one_cit = True

            # Mannually inject at the righ year
            for publi_manu_year_here in publi_manu_years:
                if int(paper.year) < publi_manu_year_here[0] and publi_manu_year_here[2]:
                    latex_subpart += publi_manu_year_here[1] + '\n\n'
                    publi_manu_year_here[2] = False

            print(paper.author[0], paper.year)
            latex_subpart = latex_subpart + ref + '\n\n'

    if not there_at_least_one_cit:
        return ''

    latex_subpart = latex_subpart + '\\end{' + bullet + '}\n\n'
    # print(latex_subpart)
    return latex_subpart


def create_latex_subpart_manually(Name_part='MY PAPERS', bullet='itemize', list_ref=list()):
    """Create a Latex sublist manually

    Parameters
    ----------
    Name_part: string, optional, default 'MY PAPERS'
                name of the latex subpart
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

    latex_subpart = ('\\vspace{-0.9cm}\n'
                     '\\textcolor{RoyalBlue}{\\section*{\large ' + Name_part + '}\n'
                     '\\vspace{-0.3cm}\hrule}\n'
                     '\\vspace{0.4cm}\n\n'
                     '\\begin{' + bullet + '} \itemsep -1pt\n\n')

    there_at_least_one_cit = False

    for ref in list(list_ref):
        there_at_least_one_cit = True
        latex_subpart = latex_subpart[1] + ref + '\n\n'

    if not there_at_least_one_cit:
        return ''

    latex_subpart = latex_subpart + '\\end{' + bullet + '}\n\n'
    # print(latex_subpart)
    return latex_subpart


def create_latex_files(researcher_name,
                       years,
                       french=False,
                       Number_authors_displayed=3,
                       phd_sec=False,
                       add_pub_manually=None):
    """Create and save a full latex file. This part should be customized depending on how you want to organize your publication list.
    I'm an instrumentalist so SPIE proceedings are important but you can customized as you see fit.
    There are currently 6 parts:
        - Major refereed papers (if researcher_name position in the author list <= Number_authors_displayed),
        - Minor refereed papers (if researcher_name position in the author list > Number_authors_displayed),
        - Major proceeding papers (if researcher_name position in the author list <= Number_authors_displayed),
        - Minor proceeding papers (if researcher_name position in the author list > Number_authors_displayed),
        - A subpart with only some white papers
        - My phd 

    Parameters
    ----------
    researcher_name : string, name of the reserachers for which this list is created
    years: tupple, range of years in the query
    french: Bool
        If true, in french, else in english
    Number_authors_displayed: int, optinal, default = 3
                number of author printed by paper. This is also the criteria used to distinguished if a paper is 'major' or 'minor'
    phd_sec: bool, optional False
        Do you want a phd section (only if your phd is on ads :-) )
    add_publi_manually: dict()
        See yaml file for help

    Returns
    ------------
    No return, latex file is directly savec
    """

    if french:
        Name_ref_imp = 'PRINCIPAUX ARTICLES'
        Name_nonref_imp = 'PRINCIPAUX ACTES DE CONFERENCES'
        Name_ref_nonimp = 'AUTRES ARTICLES'
        Name_nonref_nonimp = 'AUTRES ACTES DE CONFERENCES'

        Name_these = 'MANUSCRIT DE THESE'

        lang = 'fr'
        geom_string = ('\\documentclass[10pt, a4paper, french]{article}\n'
                       '\\usepackage[total={17.2cm,25.cm}, left=1.9cm, top=2.5cm]{geometry}\n')
        title_string = 'LISTE DE PUBLICATIONS'

    else:
        Name_ref_imp = 'MAJOR REFEREED PUBLICATIONS'
        Name_nonref_imp = 'MAJOR CONFERENCE PROCEEDINGS'
        Name_ref_nonimp = 'OTHER REFEREED PUBLICATIONS'
        Name_nonref_nonimp = 'OTHER CONFERENCE PROCEEDINGS'

        Name_these = 'PHD THESIS'

        lang = 'en'
        geom_string = ('\\documentclass[10pt]{article}\n'
                       '\\usepackage[total={6.5in,9in},left=1in,top=1in,headheight=110pt]{geometry} \n')
        title_string = 'PUBLICATION LIST'

    # words leading to a rejections for papers and proc parts (proposal, abstracts, conference w/o proc)
    reject_kw_papers = [
        'Abstracts',
        'European Planetary Science Congress',
        'VizieR',
        'JWST Proposal',
        'Thesis',
        'Space Astrophysics Landscape',
        'Bulletin of the American Astronomical Society',
        'Thirty years of Beta Pic',
        'arXiv e-prints',
    ]

    researcher_name_short = researcher_name.split(', ')[0]
    name_file = 'publication_list_' + researcher_name_short + '_' + lang + '.tex'

    latex_header = (
        geom_string + '\\usepackage{etaremune}\n'
        '\\usepackage[usenames, dvipsnames]{xcolor}\n'
        '\\usepackage[colorlinks = true,urlcolor = BrickRed, breaklinks = true]{hyperref}\n'
        '\\usepackage{fancyhdr}\n'
        '\\renewcommand{\\headrulewidth}{0pt}\n'
        '\\newcommand\\altand{\&}\n'
        '\\usepackage[nobottomtitles]{titlesec}\n'
        '\\pagestyle{fancy}\n'
        '\\rhead{}\n'
        '\\chead{}\n'
        '\\cfoot{}\n'
        '\\rfoot{}\n'
        # '\\rfoot{' + rfoot + '}\n\n'
        '\\begin{document}\n\n'
        '\\begin{center}\\begin{Large}\n'
        '\\textbf{' + title_string + '}\n'
        '\\end{Large}\\end{center}\n\n'
        '\\setcounter{section}{0}\n\n')

    latex_footer = ('\n\n'
                    '\n\n'
                    '\\end{document}\n')

    # print(name_file)
    with open(name_file, 'w') as outf:
        outf.write(latex_header + '\n\n')
        outf.write(
            create_latex_subpart(researcher_name,
                                 Name_part=Name_ref_imp,
                                 Number_authors_displayed=Number_authors_displayed,
                                 refereed=True,
                                 years=years,
                                 major=True,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate',
                                 add_publi_manually=add_pub_manually["refereed"]['major']))
        outf.write(
            create_latex_subpart(researcher_name,
                                 Name_part=Name_ref_nonimp,
                                 Number_authors_displayed=Number_authors_displayed,
                                 refereed=True,
                                 years=years,
                                 major=False,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate',
                                 add_publi_manually=add_pub_manually["refereed"]['minor']))

        outf.write(
            create_latex_subpart(researcher_name,
                                 Name_part=Name_nonref_imp,
                                 Number_authors_displayed=Number_authors_displayed,
                                 refereed=False,
                                 years=years,
                                 major=True,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate',
                                 add_publi_manually=add_pub_manually["proceeding"]['major']))
        outf.write(
            create_latex_subpart(researcher_name,
                                 Name_part=Name_nonref_nonimp,
                                 Number_authors_displayed=Number_authors_displayed,
                                 refereed=False,
                                 years=years,
                                 major=False,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate',
                                 add_publi_manually=add_pub_manually["proceeding"]['minor']))

        if len(add_pub_manually["white_paper"]) > 0:
            if french:
                Name_wp_imp = 'PAPIERS BLANCS (SELECTION)'
            else:
                Name_wp_imp = 'WHITE PAPERS (SELECTED)'

            outf.write(create_latex_subpart_manually(Name_part=Name_wp_imp, list_ref=add_pub_manually["white_paper"]))

        if phd_sec:
            outf.write(
                create_latex_subpart(researcher_name,
                                     Name_part=Name_these,
                                     years=(2014, 2014),
                                     reject_kw=None,
                                     select_kw=['Thesis'],
                                     bullet='itemize'))

        outf.write(latex_footer + '\n')


if __name__ == '__main__':

    with open(os.path.join(os.getcwd(), 'config_pub_list.yaml'), 'r') as file:
        config = yaml.safe_load(file)

    # first get a token https://ads.harvard.edu/handouts/ADS_API_handout.pdf
    ads.config.token = config["ads_config_token"]  # your ADS token
    check_ads_token()

    researcher_name = 'Mayor,  Michel'  # last name, first name
    years = (1900, 2040)  # years to be queried: (start year, end year). If None, all years (careful with old homonyms)
    french = False  # True French, False English. Default is false (English)
    Number_authors_displayed = 3
    # this parameter is the number of author that are going to be printed in the latex for a paper
    # but it is also what differentieate between an "important" paper or not which will separate in different parts

    dict_pub_manually = config["add_pub_manually"]

    lang = '_fr' if french else '_en'
    name_publi = 'publication_list_' + researcher_name.split(',')[0] + lang

    create_latex_files(researcher_name,
                       years=years,
                       french=french,
                       Number_authors_displayed=Number_authors_displayed,
                       phd_sec=True,
                       add_pub_manually=dict_pub_manually)

    os.system('pdflatex ' + name_publi + '.tex')

    print("")
    print("The h-factor of " + researcher_name + " is:", measure_h_factor(researcher_name))
    print("")

    os.system('rm *.aux|| true && rm *.log || true && rm *.out || true && rm *.fls || true && rm *.fdb_latexmk || true')
