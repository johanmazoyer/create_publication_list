import os
import time
from pylatexenc.latexencode import utf8tolatex
import ads


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
    papers = ads.SearchQuery(author=author,
                             fq=fq,
                             q=q,
                             sort='pubdate',
                             rows=rows,
                             fl=[
                                 'title', 'author', 'year', 'volume', 'page',
                                 'pub', 'identifier', 'citation', 'doi'
                             ])
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
    title = '{\\it ' + utf8tolatex(paper.title[0]) + '}'

    # build author list
    if name is None:
        # treat all author names equally and list all of them
        authors = [
            utf8tolatex(paper.author[i]) for i in range(len(paper.author))
        ]
        etal = False
    else:
        # highlight `name` in output string, if provided
        authors = []
        # name_found = False
        # dotdotdot = False
        etal = False
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
                if name_short in author:
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

        authors = ' ; '.join(authors)
    year = paper.year

    # create string with journal volume and page number
    pub = str(paper.pub)
    if paper.volume is not None:
        pub += ', ' + str(paper.volume)
    if paper.page is not None:
        pub += ', ' + str(paper.page[0])

    doi_link = ''
    if paper.doi is not None:
        # print(paper.doi[0])
        # doi_link = ("\\url{http://doi.org/" + paper.doi[0] +"}")
        # doi_link = ('\href{https://doi.org/' + paper.doi[0] + '}{doi.org/' + paper.doi[0] + '}')
        doi_link = ('\href{https://doi.org/' + paper.doi[0] + '}{DOI Link}')

    arxiv_link = ''
    for ident in paper.identifier:
        if 'ArXiv:' in ident:
            arxiv_id = ident[6:]
            arxiv_link = ('\href{https://arxiv.org/abs/' + arxiv_id +
                          '}{arxiv}')
        elif len(ident) == 10 and ident[4] == '.':
            arxiv_link = ('\href{https://arxiv.org/abs/' + ident + '}{arxiv}')

    # assemble output string as latex bullet list item
    out = ('\\item ' + authors + ' ({\\bf' + year + '}), ' + title + ', ' +
           pub)
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
    fix = {'<SUB>': '', '</SUB>': '', '─': '-', '': ''}
    for key, val in fix.items():
        if key in latex_string:
            latex_string = latex_string.replace(key, val)

    latex_string = latex_string.replace('#', '\#')
    latex_string = latex_string.replace('&', '\&')

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


def create_latex_subpart(author_name,
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

    latex_subpart = ('\\vspace{-0.5cm}\n'
                     '\\textcolor{RoyalBlue}{\\section{' + Name_part + '}\n'
                     '\\vspace{-0.25cm}\hrule}\n'
                     '\\vspace{0.6cm}\n\n'
                     '\\begin{' + bullet + '} \itemsep 0pt\n\n')

    # pull references from ads
    papers = query_papers(author_name, refereed=refereed, years=years)
    there_at_least_one_cit = False

    for paper in list(papers):
        ref = clean_string(
            select_cit(reject_cit(major_or_minor(create_paper_latex_line(
                paper, author_name),
                                                 major=major),
                                  reject_kw=reject_kw),
                       select_kw=select_kw))

        if len(ref) > 0:
            there_at_least_one_cit = True
            print(paper.author[0], paper.year)
            latex_subpart = latex_subpart + ref + '\n\n '

    if not there_at_least_one_cit:
        return ''

    latex_subpart = latex_subpart + '\\end{' + bullet + '}\n\n'
    # print(latex_subpart)
    return latex_subpart


def create_latex_subpart_manually(Name_part='MY PAPERS',
                                  list_ref=None,
                                  bullet='itemize'):
    """create a altex string for each subparts of the list

    :param out: string containing publication information

    :return out: latex string of a subpart
    """

    latex_subpart = ('\\vspace{-0.5cm}\n'
                     '\\textcolor{RoyalBlue}{\\section{' + Name_part + '}\n'
                     '\\vspace{-0.25cm}\hrule}\n'
                     '\\vspace{0.6cm}\n\n'
                     '\\begin{' + bullet + '} \itemsep 0pt\n\n')

    there_at_least_one_cit = False

    for ref in list(list_ref):
        there_at_least_one_cit = True
        latex_subpart = latex_subpart + ref + '\n\n'

    if not there_at_least_one_cit:
        return ''

    latex_subpart = latex_subpart + '\\end{' + bullet + '}\n\n'
    # print(latex_subpart)
    return latex_subpart


def create_latex_files(author_name, years, french=False):

    if french:
        Name_ref_imp = 'PRINCIPAUX ARTICLES'
        Name_nonref_imp = 'PRINCIPAUX ACTES DE CONFERENCES'
        Name_ref_nonimp = 'AUTRES ARTICLES'
        Name_nonref_nonimp = 'AUTRES ACTES DE CONFERENCES'

        Name_wp_imp = 'PAPIERS BLANCS (SELECTION)'
        # Name_wp_imp = 'Papiers blancs (selections)'

        Name_these = 'MANUSCRIT DE THESE'

        lang = 'fr'
        geom_string = (
            '\\documentclass[11pt, a4paper, french]{article}\n'
            '\\usepackage[total={17.2cm,25.cm}, left=1.9cm, top=2.5cm]{geometry}\n'
        )
        title_string = 'LISTE DES PUBLICATIONS'

    else:
        Name_ref_imp = 'MAJOR REFEREED PUBLICATIONS'
        Name_nonref_imp = 'MAJOR CONFERENCE PROCEEDINGS'
        Name_ref_nonimp = 'OTHER REFEREED PUBLICATIONS'
        Name_nonref_nonimp = 'OTHER CONFERENCE PROCEEDINGS'

        Name_wp_imp = 'WHITE PAPERS (SELECTED)'

        Name_these = 'PHD THESIS'

        lang = 'en'
        geom_string = (
            '\\documentclass[11pt]{article}\n'
            '\\usepackage[total={6.5in,9in},left=1in,top=1in,headheight=110pt]{geometry} \n'
        )
        title_string = 'PUBLICATION LIST'

    # words leading to a rejections for papers and proc parts (proposal, abstracts, conference w/o proc)
    reject_kw_papers = [
        'Abstracts', 'European Planetary Science Congress', 'VizieR',
        'arXiv e-prints', 'Thesis', 'Space Astrophysics Landscape',
        'Bulletin of the American Astronomical Society','Thirty years of Beta Pic'
    ]
    
    name_short = author_name.split(', ')[0]
    name_file = 'publication_list_' + name_short + '_' + lang + '.tex'

    latex_header = (
        geom_string + '\\usepackage{etaremune}\n'
        '\\usepackage[usenames, dvipsnames]{xcolor}\n'
        '\\usepackage[colorlinks = true,urlcolor = BrickRed, breaklinks = true]{hyperref}\n'
        '\\usepackage{fancyhdr}\n'
        '\\renewcommand{\\headrulewidth}{0pt}\n'
        '\\pagestyle{fancy}\n'
        '\\rhead{}\n'
        '\\chead{}\n'
        '\\cfoot{}\n'
        '\\rfoot{\\href{http://johanmazoyer.com}{johanmazoyer.com}}\n\n'
        '\\begin{document}\n\n'
        '\\begin{center}\\begin{Large}\n'
        '\\textbf{' + title_string + '}\n'
        '\\end{Large}\\end{center}\n\n'
        '\\setcounter{section}{0}\n\n')

    latex_footer = ('\\end{document}\n')

    # print(name_file)
    with open(name_file, 'w') as outf:
        outf.write(latex_header + '\n\n')
        outf.write(
            create_latex_subpart(author_name,
                                 Name_part=Name_ref_imp,
                                 refereed=True,
                                 years=years,
                                 major=True,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate'))
        outf.write(
            create_latex_subpart(author_name,
                                 Name_part=Name_ref_nonimp,
                                 refereed=True,
                                 years=years,
                                 major=False,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate'))

        outf.write(
            create_latex_subpart(author_name,
                                 Name_part=Name_these,
                                 years=(2014, 2014),
                                 reject_kw=None,
                                 select_kw=['Thesis'],
                                 bullet='itemize'))

        outf.write(
            create_latex_subpart(author_name,
                                 Name_part=Name_nonref_imp,
                                 refereed=False,
                                 years=years,
                                 major=True,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate'))
        outf.write(
            create_latex_subpart(author_name,
                                 Name_part=Name_nonref_nonimp,
                                 refereed=False,
                                 years=years,
                                 major=False,
                                 reject_kw=reject_kw_papers,
                                 bullet='enumerate'))

        ref_wp = [
            '\\item Boccaletti, A. ; Chauvin, G. ; Mouillet, D. et al. ({\\bf  2020}), {\it SPHERE+: Imaging young Jupiters down to the snowline}, arXiv e-prints, \href{https://ui.adsabs.harvard.edu/abs/arXiv:2003.05714}{arXiv:2003.05714}',
            '\\item Gaudi, B. S. ; Seager, S. ; Mennesson, B. et al. ({\\bf  2020}), {\it The Habitable Exoplanet Observatory (HabEx) Mission Concept Study Final Report}, arXiv e-prints,  \href{https://ui.adsabs.harvard.edu/abs/arXiv:2001.06683}{arXiv:2001.06683}',
            '\\item The LUVOIR Team ({\\bf  2019}), {\it The LUVOIR Mission Concept Study Final Report}, arXiv e-prints, \href{https://ui.adsabs.harvard.edu/abs/arXiv:1912.06219}{arXiv:1912.06219}',
            '\\item {\\bf  Mazoyer, J.} ; Baudoz, P. ; Belikov, R. et al. ({\\bf  2019}), {\it High-Contrast Testbeds for Future Space-Based Direct Imaging Exoplanet Missions}, Bulletin of the American Astronomical Society, 51, 101, \href{https://ui.adsabs.harvard.edu/abs/arXiv:1907.09508}{arXiv:1907.09508}'
        ]

        outf.write(
            create_latex_subpart_manually(Name_part=Name_wp_imp,
                                          list_ref=ref_wp))
        outf.write(latex_footer + '\n')


if __name__ == '__main__':

    ads.config.token = 'x58IUp8AXJ7WzCZyj1Py9zc3liBKaIvRjIwodThV'  # your ADS token
    author_name = 'Mazoyer, Johan'  # last name, first name
    years = (2011, 2030)  # years to be queried: (start year, end year). If None, all years (careful with old homonyms)
    french = False # True French, False English, default is false
    Number_authors_displayed=3
    

    for french in [True, False]:
        if french:
            name_publi = 'publication_list_Mazoyer_fr'
            name_cv = 'CV_Mazoyer_fr'
            name_combi = 'CV_publi_Mazoyer_fr'
        else:
            name_publi = 'publication_list_Mazoyer_en'
            name_cv = 'CV_Mazoyer_en'
            name_combi = 'CV_publi_Mazoyer_en'

        
        create_latex_files(author_name, years=years, french=french)
        os.system('pdflatex ' + name_publi + '.tex')

        time.sleep(5)
        os.system('pdflatex ' + name_publi + '.tex')
        time.sleep(5)
        os.system('pdflatex ' + name_publi + '.tex')
        time.sleep(5)
        os.system('cp ' + name_publi + '.pdf ../mywebpage/CV_publi_website/')
        os.system(
            'cd ../mywebpage/CV_publi_website/ && gs -dBATCH -dNOPAUSE -dPDFSETTINGS=/prepress -dPrinted=false -q -sDEVICE=pdfwrite -sOutputFile='
            + name_combi + '.pdf ' + name_cv + '.pdf ' + name_publi + '.pdf')

    os.system(
        'cd ../mywebpage/ && git add . && git commit -m "automatically update list publications" && git push'
    )
    os.system('rm *.aux && rm *.log && rm *.out')
