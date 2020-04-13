import os
import time
from pylatexenc.latexencode import utf8tolatex
import ads


ads.config.token = 'x58IUp8AXJ7WzCZyj1Py9zc3liBKaIvRjIwodThV'  # your ADS token
author_name = 'Mazoyer, Johan'  # last name, first name
years = (2011, 2030) # years to be queried: (start year, end year)
french = False



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
                             fl=['title', 'author', 'year', 'volume',
                                 'page', 'pub', 'identifier', 'citation','doi'])

    return list(papers)

def create_paper_latex_line(paper, name=None):
    """create the latex document in strings using latex encoding

    :param paper: ads publication object
    :param name: string or `None`, name that will be highlighted in latex,
                 default: `None`

    :return: str, latex encoded string for paper
    """
    out = ''
    # put paper title in italic font
    title = '{\\it ' + utf8tolatex(paper.title[0]) + '}'

    # build author list
    if name is None:
        # treat all author names equally and list all of them
        authors = [utf8tolatex(paper.author[i])
                   for i in range(len(paper.author))]
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
            if len(author.split(','))>1:
                prenoms = author.split(',')[1]
            else:
                prenoms = '?'
            prenoms = prenoms.replace("-", " -")
            prenoms = prenoms.split(' ')
            while True:
                try :
                    prenoms.remove('')
                except ValueError:
                    break
    
            for prenomj, prenom  in enumerate(prenoms):
                if prenom[0] == '-':
                    prenoms[prenomj] =  prenom[0:2] + '.'
                elif prenom[0] == '{':
                    end = prenom.find('}')
                    prenoms[prenomj] = prenom[0:end+1] + '.'
                else:
                    prenoms[prenomj] = prenom[0] + '.'

            author = nom + ", "+" ".join(prenoms)
            #print(author)
            
            if i < 3:
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






    # arxiv_link = ''
    # for ident in paper.identifier:
    #     if 'ArXiv:' in ident:
    #         arxiv_id = ident[6:]
    #         arxiv_link = ('\href{https://arxiv.org/abs/' +
    #                       arxiv_id + '}{arxiv}')
    #     elif len(ident) == 10 and ident[4] == '.':
    #         arxiv_link = ('\href{https://arxiv.org/abs/' +
    #                       ident + '}{arxiv}')

    # assemble output string as latex bullet list item
    out = ('\\item ' + authors + ' ({\\bf'   + year + '}), ' + title +
           ', ' + pub)
    if doi_link != '':
        out += ', ' + doi_link
    # if arxiv_link != '':
    #     out += ', ' + arxiv_link

    # add number of citations, if available
    if paper.citation is not None and len(paper.citation) > 1:
        out += ', ' + str(len(paper.citation)) + ' citations'
    elif paper.citation is not None and len(paper.citation) == 1:
        out += ', ' + str(len(paper.citation)) + ' citation'

    return out

def fixme(latex_string):
    """fix/reject citation substrings

    :param out: string containing publication information

    :return out: string
    """

    # words leading to a rejection
    reject = ['Abstracts', 'European Planetary Science Congress','VizieR',
                'arXiv e-prints',
                'Bulletin of the American Astronomical Society',
                'Thesis']
    for s in reject:
        if s in latex_string:
            return ''

    # substrings to be replaced
    fix = {'<SUB>': '',
           '</SUB>': '',
           '─': '-',
           '': ''}
    for key, val in fix.items():
        if key in latex_string:
            latex_string = latex_string.replace(key, val)

    latex_string = latex_string.replace('#', '\#')

    return latex_string

def major_or_minor(latex_string, major = True):
    """sort major and minor publications

    :param out: string containing publication information

    :return out: string
    """
    if major: 
        if not name_short in latex_string:
            return ''
    else:
        if name_short in latex_string:
            return ''

    return latex_string

def create_latex_subpart(author_name, years, refereed=True, major=True, french=False):
    """create a altex string for each subparts of the list

    :param out: string containing publication information

    :return out: latex string of a subpart
    """

    if refereed:
        if french:
            Name_doc = 'ARTICLES' 
        else:
            Name_doc = 'REFEREED PUBLICATIONS'
    else:
        if french:
            Name_doc = 'ACTES DE CONFERENCES' 
        else:
            Name_doc = 'CONFERENCE PROCEEDINGS'
    
    if major:
        if french:
            Name_doc = 'PRINCIPAUX ' +Name_doc 
        else:
            Name_doc = 'MAJOR ' +  Name_doc 
    else:
        if french:
            Name_doc = 'AUTRES ' +Name_doc 
        else:
            Name_doc = 'OTHER ' +  Name_doc 

    latex_subpart =(
        '\\vspace{-0.5cm}\n'
        '\\textcolor{RoyalBlue}{\\section{'+Name_doc+'}\n'
        '\\vspace{-0.25cm}\hrule}\n'
        '\\vspace{0.6cm}\n\n'
        '\\begin{etaremune} \itemsep 0pt\n\n'
        )
    
    # pull references from ads
    papers = query_papers(author_name, refereed=refereed, years=years)
    
    for paper in list(papers):
        ref = fixme(major_or_minor(create_paper_latex_line(paper, author_name), major = major))
        if len(ref) > 0:
            print(paper.author[0], paper.year)
            latex_subpart = latex_subpart + ref + '\n\n '
    
    latex_subpart = latex_subpart + '\\end{etaremune}\n\n'
    # print(latex_subpart)
    return latex_subpart

def create_latex_subpart_these(french=False):
    """create a altex string just for my phd

    :param out: string containing publication information

    :return out: latex string of a subpart
    """

    if french:
        Name_doc = 'MANUSCRIT DE THESE' 
    else:
        Name_doc = 'PHD THESIS'
   

    latex_subpart =(
        '\\vspace{-0.5cm}\n'
        '\\textcolor{RoyalBlue}{\\section{'+Name_doc+'}\n'
        '\\vspace{-0.25cm}\hrule}\n'
        '\\vspace{0.6cm}\n\n'
        '\\begin{itemize} \itemsep 0pt\n\n'
        )
    
    # pull references from ads
    papers = query_papers('Mazoyer, Johan', years=(2014,2014))
    
    for paper in list(papers):
        ref = create_paper_latex_line(paper, author_name)
        if 'Thesis' in ref:
            print(paper.author[0], paper.year)
            latex_subpart = latex_subpart + ref + '\n\n '
    
    latex_subpart = latex_subpart + '\\end{itemize}\n\n'
    # print(latex_subpart)
    return latex_subpart

def create_latex_files(author_name, years, french=False):

    if french:
        lang = 'fr'
        geom_string =  ('\\documentclass[11pt, a4paper, french]{article}\n'
                        '\\usepackage[total={17.2cm,25.cm}, left=1.9cm, top=2.5cm]{geometry}\n'
                        )
        title_string = 'LISTE DES PUBLICATIONS'
    else:
        lang = 'en'
        geom_string =  ('\\documentclass[11pt]{article}\n'
                        '\\usepackage[total={6.5in,9in},left=1in,top=1in,headheight=110pt]{geometry} \n'
                        )
        title_string = 'PUBLICATION LIST'

    name_file = 'publication_list_' + name_short + '_' +lang+'.tex'


    





    latex_header = (
        geom_string+
        '\\usepackage{etaremune}\n'
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
        '\\textbf{'+title_string+'}\n'
        '\\end{Large}\\end{center}\n\n'
        '\\setcounter{section}{0}\n\n'
        )

    latex_footer = (
        '\\end{document}\n')


    # print(name_file)
    with open(name_file, 'w') as outf:
        outf.write(latex_header + '\n\n')
        outf.write(create_latex_subpart(author_name, refereed=True, years=years, major = True, french = french)+ '\n\n')
        outf.write(create_latex_subpart(author_name, refereed=True, years=years, major = False, french = french)+ '\n\n')
        if name_short == 'Mazoyer':
            outf.write(create_latex_subpart_these())
        
        outf.write(create_latex_subpart(author_name, refereed=False, years=years, major = True, french = french)+ '\n\n')
        outf.write(create_latex_subpart(author_name, refereed=False, years=years, major = False, french = french)+ '\n\n')
        outf.write(latex_footer + '\n')

if __name__ == '__main__':
    name_short = author_name.split(', ')[0]
    
    for french in [True,False]:
        if french:
            name_publi = 'publication_list_Mazoyer_fr'
            name_cv = 'CV_Mazoyer_fr'
            name_combi = 'CV_publi_Mazoyer_fr'
        else: 
            name_publi = 'publication_list_Mazoyer_en'
            name_cv = 'CV_Mazoyer_en'
            name_combi = 'CV_publi_Mazoyer_en'
        
        create_latex_files(author_name, years=years, french = french)
        time.sleep(5)
        os.system('pdflatex ' +name_publi +'.tex')
        time.sleep(5)
        os.system('cp ' +name_publi+'.pdf ../mywebpage/CV_publi_website/') 
        os.system('cd ../mywebpage/CV_publi_website/ && gs -dBATCH -dNOPAUSE -dPDFSETTINGS=/prepress -q -sDEVICE=pdfwrite -sOutputFile='+name_combi+'.pdf ' + name_cv + '.pdf '+ name_publi+ '.pdf')
        os.system('cd ../mywebpage/ && git add . && git commit -m "automatically update '+name_combi+ '.pdf' + ' " && git push')

    os.system('rm *.aux && rm *.log && rm *.out')

