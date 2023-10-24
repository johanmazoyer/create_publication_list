from create_publist import *


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
    # you can use \item[$\\bullet$] to avoid numbering them if they are not accepted yet

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