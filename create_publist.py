from pylatexenc.latexencode import utf8tolatex
import ads

ads.config.token = 'x58IUp8AXJ7WzCZyj1Py9zc3liBKaIvRjIwodThV'  # your ADS token
author_name = 'Mazoyer, Johan'  # last name, first name
years = (1995, 2020) # years to be queried: (start year, end year)
refereed = False # if True, only refereed publications will be queried;
                # if False, only non-refereed publications will be queried


if refereed:
    Name_doc = 'Refereed Publications'
else:
    Name_doc = 'Conference Proceedings (SPIE, AO4ELT)'

name_short = author_name.split(', ')[0]


latex_header = (
    '\\documentclass[11pt]{article}\n'
    '\\usepackage[inner=1in,outer=1in,top=1in,bottom=1in]{geometry}\n'
    '\\usepackage{etaremune}\n\n'
    '\\usepackage[usenames, dvipsnames]{xcolor}\n\n'
    '\\usepackage[colorlinks = true,urlcolor = BrickRed, breaklinks = true]{hyperref}\n\n'
    '\\begin{document}\n\n'
    '\\section*{'+Name_doc+'}\n\n'
    '\\begin{etaremune} \itemsep 0pt\n')

latex_footer = (
    '\\end{etaremune}\n'
    '\\end{document}\n')

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

def create_latex(paper, name=None):
    """turn ads publication objects into strings using latex encoding

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

def fixme(out):
    """fix/reject citation substrings

    :param out: string containing publication information

    :return out: string
    """

    # words leading to a rejection
    reject = ['Abstracts', 'European Planetary Science Congress','VizieR',
                'arXiv e-prints',
                'Bulletin of the American Astronomical Society',
                'Lunar and Planetary Science Conference', 'AO4ELT']
    for s in reject:
        if s in out:
            return ''

    # substrings to be replaced
    fix = {'<SUB>': '',
           '</SUB>': '',
           '─': '-',
           '': ''}
    for key, val in fix.items():
        if key in out:
            out = out.replace(key, val)

    out = out.replace('#', '\#')

    return out

# pull references from ads
papers = query_papers(author_name, refereed=refereed, years=years)
# write results to file
if refereed:
    ref = 'ref'
else:
    ref = 'proc'

name_file = 'publication_list_'+ref+'_'+name_short+'.tex'
print(name_file)
with open(name_file, 'w') as outf:
    outf.write(latex_header + '\n\n')
    for paper in list(papers):
        ref = fixme(create_latex(paper, author_name))
        if len(ref) > 0:
            print(paper.author[0], paper.year)
            outf.write(ref + '\n\n')
    outf.write(latex_footer + '\n')