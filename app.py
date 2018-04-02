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

@app.route('/opening', methods=['POST'])
def opening():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processOpeningRequest(req)

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
    keywordList = parameters.get("keywords")
    keywords = ""
    if keywordList:
        for term in keywordList:
            keywords += term + " "
    analyst = parameters.get("analyst")
    count = parameters.get("count")
        
    data = processSearch(keywords,analyst, int(count) if count else 3)    
   
    return makeAPIAIWebhookResult(data)

def processOpeningRequest(req):
    requestObj = req.get("request")
    if requestObj["type"] == "IntentRequest" AND requestObj["dialogState"] != "COMPLETED":
        resp = {
            "version":"1.0",
            "response": {
                "type": "Dialog.Delegate",
                "intent": requestObj["intent"],
                "shouldEndSession":False  ## required for the Alexa test harness - even though the docs say it's optional
            }
        }
        print(JSON.dumps(resp)
        return resp
    else:
        return {
            "version":"1.0",
            "response": {
                "shouldEndSession":False  ## required for the Alexa test harness - even though the docs say it's optional
            }
        }      


def processAlexaRequest(req):
    parameters = req.get("request").get("intent").get("slots")
    keywords = parameters.get("topicsslot").get("value")
    analyst = parameters.get("analystsslot").get("value")

    data = processSearch(keywords, analyst, 10)

    return makeAlexaWebhookResult(data)


def processSearch(keywords, analyst, count):
    baseurl = "https://www.gartner.com/search/site/premiumresearch/simple?"
    search_string = ""
    if keywords:
        search_string += keywords
    if analyst and (analyst != "Any"):
        search_string += " author:" + analyst

    yql_url = baseurl + urllib.parse.urlencode({'keywords': search_string})
    print(yql_url)

    result = urllib.request.urlopen(yql_url)

    result_soup = BeautifulSoup(result, 'html.parser')
    doc_results = result_soup.find_all("div", class_="searchResultRow")
    doc_list = []

    for doc in doc_results:
        doc_item = {}
        doc_item['title'] = doc.select(".search-result")[0].text.strip()
        doc_item['url'] = doc.select(".search-result")[0].attrs["href"]
        doc_item['analysts'] = ""
        analysts = doc.find("p", class_="results-analyst").find_all("a")
        for analyst in analysts:
            doc_item['analysts'] += analyst.text.strip() + ", "
        doc_list.append(doc_item)
        if count != 0 and len(doc_list) == count:
            break

    data = {'keywords': keywords, 'analyst': analyst, 'results':doc_list, 'url':yql_url}
    return data


def makeAlexaWebhookResult(data):
    keywords = data.get('keywords')
    speech = ""
    if keywords is None:
        speech = "Sorry, I didn't detect any valid keywords"
    else:
        results = data.get('results')
        result_count = len(results)
        if results is None or result_count == 0:
            speech = "Sorry, I didn't find any results"
        else:
            speech = "I found " + str(len(results))+ " results for "
            top = 3 #maximum of three results on Alexa...just takes too long to read otherwise.
            if len(results) < top:
                top = len(results)
            speech += keywords + ", the top "+ str(top) + " results are: "
            for item in range(0, top):
                speech += str(item+1) + ". " + results[item].get('title')
                speech += " by " + results[item].get('analysts') + "\n "
    print("Response:")
    print(speech)
    return {
        "version":"1.0",
        "response": {
            "outputSpeech": {
                "type": "PlainText",
                "text": speech},
            "shouldEndSession":True  ## required for the Alexa test harness - even though the docs say it's optional
        }
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
