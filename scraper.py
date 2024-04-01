# ~ Import packages ~ #
from google_patent_scraper import scraper_class
import json, time
import pandas as pd
import concurrent.futures
import pprint

MAX_THREADS = 30

root_patent = input('Enter patent code: ')

scraper=scraper_class()

patents = {
    'patent_code': [root_patent],
    'direction': ['root'],
    'level': [0],
    'count': [1],
    'url': [f'https://patents.google.com/patent/{root_patent}']
}

df_patents = pd.DataFrame(patents)

def update_count(code, dir, level, url):
    if code in df_patents['patent_code'].values:
        df_patents.loc[df_patents['patent_code'] == code, 'count'] += 1
    else:
        df_patents.loc[len(df_patents)] = [code, dir, level, 1, url]

def get_parent_patents(children, level):
    parent_nums = []
    err_1, soup_1, url_1 = scraper.request_single_patent(children)
    parsed_child = scraper.get_scraped_data(soup_1,children,url_1)

    for parent_patent in json.loads(parsed_child['backward_cite_no_family']):
        patent_number = parent_patent['patent_number']
        err_2, soup_2, url_2 = scraper.request_single_patent(patent_number)
        update_count(patent_number, 'parent', level, url_2)
        parent_nums.append(patent_number)
    
    return parent_nums

def get_child_patents(parents, level):
    child_nums = []
    err_1, soup_1, url_1 = scraper.request_single_patent(parents)
    parsed_parent = scraper.get_scraped_data(soup_1,parents,url_1)
    
    for child_patent in json.loads(parsed_parent['forward_cite_no_family']):
        patent_number = child_patent['patent_number']
        err_2, soup_2, url_2 = scraper.request_single_patent(patent_number)
        update_count(patent_number, 'child', level, url_2)
        child_nums.append(patent_number)
    
    return child_nums

def get_patents(subpatents, level, is_parent):
    patent_codes = []

    threads = min(MAX_THREADS, len(subpatents))
    threads = 1 if threads == 0 else threads
    levels = [level] * len(subpatents)
    
    if is_parent:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            parent_codes = list(executor.map(get_child_patents, subpatents, levels))
            # print(f'parent_codes = {parent_codes}')
            if parent_codes:
                patent_codes.extend(max(parent_codes, key=len))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            child_codes = list(executor.map(get_parent_patents, subpatents, levels))
            # print(f'child_codes = {child_codes}')
            if child_codes:
                patent_codes.extend(max(child_codes, key=len))
    
    return patent_codes

if __name__ == "__main__":
    t0 = time.time()

    parent_nums   = get_patents([root_patent], 1, True)
    gparent_nums  = get_patents(parent_nums, 2, True)
    ggparent_nums = get_patents(gparent_nums, 3, True)

    child_nums   = get_patents([root_patent], 1, False)
    gchild_nums  = get_patents(child_nums, 2, False)
    ggchild_nums = get_patents(gchild_nums, 3, False)

    t1 = time.time()

    df_sorted_patents = df_patents.sort_values(by=['count'], ascending=False)
    pd.set_option('display.max_rows', None)
    print(f'Total Count: {len(df_patents)}')
    print(f'{t1-t0} seconds to download {len(df_patents)} patent codes.')
    df_sorted_patents.to_csv('patent_codes.csv')