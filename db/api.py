import urllib.request
import json
import html

suggestion_id = 395



def get_data(url):
    with urllib.request.urlopen(url) as response:
        assert(response.code == 200)
        data = json.loads(response.read())
        return data

def get_package(package = "", id = ""):
    if package != "":
        url = (
            "https://data.gov.hr/ckan/api/action/package_search?q=" +
            '"' + package + '"'
        )
        return get_data(url)
    elif id != "":
        url = ("https://data.gov.hr/ckan/api/action/package_show?id=" + id)
        return get_data(url)

def get_suggestions():
    data = get_data("https://data.gov.hr/Suggestions/selectAllRow")["root"]
    res = []
    for el in data:
        res.append
        (
            {
                "id"          : el["suggestionId"],
                "text"        : html.unescape(el["description"]),
                "title"       : el["title"],
                "datetime"    : el["dateTime"],
                "issueId"     : "",
                "datasetId"   : el["datasetId"] 
            }
        )
    return res

def get_suggestion(id = 0, datasetName = ""):
    data = get_data("https://data.gov.hr/Suggestions/selectAllRow")
    
    if id != 0:
        for d in data['root']:
            if d['suggestionId'] == id:
                return { 'data': d }
    
    elif datasetName != "":
        for d in data['root']:
            if d['datasetName'] == datasetName:
                return { 'data': d }
    
packages    = get_data("https://data.gov.hr/ckan/api/action/package_list")
suggestions = get_suggestions()
