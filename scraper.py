# ~ Import packages ~ #
from google_patent_scraper import scraper_class
import json, time
import pandas as pd
import concurrent.futures
from pprint import pprint

MAX_THREADS = 30
scraper = scraper_class()

patents = {
    'patent_code': [],
    'direction': [],
    'level': [],
    'count': [],
    'url': []
}

def add_patent(code, dir, level):
    patents['patent_code'].append(code)
    patents['direction'].append(dir)
    patents['level'].append(level)
    patents['count'].append(1)
    patents['url'].append(f'https://patents.google.com/patent/{code}')

def update_count(code, dir, level):
    if code in patents['patent_code']:
        index = patents['patent_code'].index(code)
        patents['count'][index] += 1
    else:
        add_patent(code, dir, level)

def get_parent_patents(child, level):
    parent_codes = []
    err_1, soup_1, url_1 = scraper.request_single_patent(child)
    parsed_child = scraper.get_scraped_data(soup_1, child, url_1)

    for parent in json.loads(parsed_child['forward_cite_no_family']):
        parent_code = parent['patent_number']
        update_count(parent_code, 'parent', level)
        parent_codes.append(parent_code)
    
    for parent in json.loads(parsed_child['forward_cite_yes_family']):
        parent_code = parent['patent_number']
        update_count(parent_code, 'parent', level)
        parent_codes.append(parent_code)
    
    return parent_codes

def get_child_patents(parent, level):
    child_codes = []
    err_1, soup_1, url_1 = scraper.request_single_patent(parent)
    parsed_parent = scraper.get_scraped_data(soup_1, parent, url_1)

    for child in json.loads(parsed_parent['backward_cite_no_family']):
        child_code = child['patent_number']
        update_count(child_code, 'child', level)
        child_codes.append(child_code)
    
    for child in json.loads(parsed_parent['backward_cite_yes_family']):
        child_code = child['patent_number']
        update_count(child_code, 'child', level)
        child_codes.append(child_code)

    return child_codes

def get_patents(subpatents, level, is_parent):
    patent_codes = []

    threads = min(MAX_THREADS, len(subpatents))
    threads = 1 if threads == 0 else threads
    levels = [level] * len(subpatents)
    
    if is_parent:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            parent_codes = list(executor.map(get_child_patents, subpatents, levels))
            flattened_parent_codes = [x for xs in parent_codes for x in xs]
            patent_codes.extend(flattened_parent_codes)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            child_codes = list(executor.map(get_parent_patents, subpatents, levels))
            flattened_child_codes = [x for xs in child_codes for x in xs]
            patent_codes.extend(flattened_child_codes)
    
    return patent_codes

if __name__ == "__main__":
    t0 = time.time()

    # get root patent
    # root_patent = input('Enter patent code: ')
    root_patent = 'US11222684B2'

    # add it to dict
    add_patent(root_patent, 'root', 0)

    # get parent citations
    print('--------------- PARENT CODES ---------------')
    parent_nums   = get_patents([root_patent], 1, True)
    gparent_nums  = get_patents(parent_nums, 2, True)
    ggparent_nums = get_patents(gparent_nums, 3, True)

    # get child citations
    print('-------------- CHILDREN CODES --------------')
    child_nums   = get_patents([root_patent], 1, False)
    gchild_nums  = get_patents(child_nums, 2, False)
    ggchild_nums = get_patents(gchild_nums, 3, False)

    t1 = time.time()
    
    df_patents = pd.DataFrame(patents, columns=['patent_code', 'direction', 'level', 'count', 'url'])
    df_sorted_patents = df_patents.sort_values(by=['count'], ascending=False)

    print(df_sorted_patents)
    print(f'{t1-t0} seconds to download {len(df_patents)} patent codes.')

    df_sorted_patents.to_csv(f'{root_patent}.csv')