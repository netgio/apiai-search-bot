#!/usr/bin/env python

import urllib.parse
import urllib.request
import json
import os
from bs4 import BeautifulSoup

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processAPIAIRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

@app.route('/alexa', methods=['POST'])
def alexa():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processAlexaRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def processAPIAIRequest(req):
    if req.get("result").get("action") != "gartnerSearchRequest":
        return {}
    parameters = req.get("result").get("parameters")
    keywords = parameters.get("keywords")
    analyst = parameters.get("analyst")
    
    data = processSearch(keywords,analyst)    
   
    return makeAPIAIWebhookResult(data)


def processAlexaRequest(req):
    parameters = req.get("request").get("intent").get("slots")
    keywords = parameters.get("topicsslot").get("value")
    analyst = parameters.get("analystsslot").get("value")

    data = processSearch(keywords, analyst)

    return makeAlexaWebhookResult(data)

    
def processSearch(keywords, analyst):
    baseurl = "https://www.gartner.com/search/site/premiumresearch/simple?"
    searchString = ""
    if keywords:
        searchString += keywords
    if analyst:
        searchString += " author:" + analyst
    yql_url = baseurl + urllib.parse.urlencode({'keywords': searchString})
    print(yql_url)

    result = urllib.request.urlopen(yql_url)
    
    result_soup = BeautifulSoup(result, 'html.parser')
    docResults = result_soup.find_all("div", class_="searchResultRow")
    docList = []
    for doc in docResults:
        docItem = {}
        docItem['title'] = doc.select(".search-result")[0].text.strip()
        docItem['url'] = doc.select(".search-result")[0].attrs["href"]
        docItem['analysts'] = ""
        analysts = doc.find("p", class_="results-analyst").find_all("a")
        for analyst in analysts:
            docItem['analysts'] += analyst.text.strip() + " "
        docList.append(docItem)

    data = {'keywords': keywords, 'analyst': analyst, 'results':docList, 'url':yql_url}
    return data


def makeAlexaWebhookResult(data):
    keywords = data.get('keywords')
    if keywords is None:
        return {}

    results = data.get('results')
    if results is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "I found " + str(len(results))+ " results for " + keywords + " including "
    
    for res in results:
        speech += res.get('title') + " by " + res.get('analysts') + "\n "
    
    print("Response:")
    print(speech)

    return {
        "version":"1.0",
        "outputSpeech": {
            "type": "PlainText",
            "text": speech}
    }

def makeAPIAIWebhookResult(data):
    
    keywords = data.get('keywords')
    if keywords is None:
        return {}

    results = data.get('results')
    if results is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "I found " + str(len(results))+ " results for " + keywords + " including "
    slack_text = "Found " + str(len(results)) + " results for " + keywords + ":"

    for res in results:
        speech += res.get('title') + " by " + res.get('analysts') + "\n "
        slack_text += "\n<" + res.get('url') + "|" + res.get('title') + "> by " + res.get('analysts')

    print("Response:")
    print(speech)

    slack_message = {
        "text": slack_text
    }

    print(json.dumps(slack_message))

    return {
        "speech": speech,
        "displayText": speech,
        "data": {"slack": slack_message},
        # "contextOut": [],
        "source": "apiai-gartner-search-bot"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print ("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
