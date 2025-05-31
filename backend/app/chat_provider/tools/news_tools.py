import json
from typing import Any, Dict
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langchain_community.tools import (
    DuckDuckGoSearchResults,
)
import requests
from langchain_core.tools import tool


yahoo_finance_news_tool = YahooFinanceNewsTool()
duckduckgo_news_search_tool = DuckDuckGoSearchResults(backend="news")


@tool
def fetch_finance_news(stock_symbol: str) -> Dict[str, Any]:
    """
    Fetch finance news for a given stock symbol from Yahoo Finance.

    Args:
        stock_symbol (str): The stock symbol to fetch news for (e.g., 'AAPL')

    Returns:
        Dict[str, Any]: JSON response containing finance news

    Raises:
        ValueError: If stock symbol is invalid or empty
        requests.exceptions.RequestException: For network-related errors
        json.JSONDecodeError: If response is not valid JSON
        KeyError: If expected data structure is not in response
    """
    if not stock_symbol or not isinstance(stock_symbol, str):
        raise ValueError("Stock symbol must be a non-empty string")

    url = f"https://finance.yahoo.com/xhr/ncp?location=US&queryRef=qsp&serviceKey=ncp_fin&symbols={stock_symbol}&lang=en-US&region=US"

    payload = '{"serviceConfig":{"count":40,"snippetCount":12},"session":{"consent":{"allowContentPersonalization":true,"allowCrossDeviceMapping":true,"allowFirstPartyAds":true,"allowSellPersonalInfo":true,"canEmbedThirdPartyContent":true,"canSell":true,"consentedVendors":[],"allowAds":true,"allowOnlyLimitedAds":false,"rejectedAllConsent":false,"allowOnlyNonPersonalizedAds":false},"authed":"0","ynet":"0","ssl":"1","spdy":"0","ytee":"0","mode":"normal","tpConsent":true,"site":"finance","adblock":"0","bucket":["prebid-bidderconfig-ttdop-ctrl","addensitylevers-test","designSystemUpgradeButton-2"],"colo":"sg3","device":"desktop","bot":"0","browser":"chrome","app":"unknown","ecma":"modern","environment":"prod","gdpr":false,"lang":"en-US","dir":"ltr","intl":"us","network":"broadband","os":"mac os x","partner":"none","region":"US","time":1748519875678,"tz":"Asia/Jakarta","usercountry":"ID","rmp":"0","webview":"0","feature":["awsCds","disableInterstitialUpsells","disableServiceRewrite","disableSubsSpotlightNav","disableBack2Classic","disableYPFTaxArticleDisclosure","enable1PVideoTranscript","enableAdRefresh20s","enableAnalystRatings","enableAPIRedisCaching","enableArticleCSN","enableArticleRecommendedVideoInsertion","enableArticleRecommendedVideoInsertionTier34","enableCGAuthorFeed","enableChartbeat","enableChatSupport","enableCompare","enableContentOfferVertical","enableCompareConvertCurrency","enableConsentAndGTM","enableFeatureEngagementSystem","enableCrumbRefresh","enableCSN","enableCurrencyConverter","enableDarkMode","enableDockAddToFollowing","enableDockCondensedHeader","enableDockNeoOptoutLink","enableDockPortfolioControl","enableExperimentalDockModules","enableFollow","enableEntityDiscover","enableEntityDiscoverInStream","enableFollowTopic","enableLazyQSP","enableLiveBlogStatus","enableLivePage","enableLSEGTopics","enableStreamingNowBar","enableLocalSpotIM","enableMarketsLeafHeatMap","enableMultiQuote","enableMyMoneyOptIn","enableNeoBasicPFs","enableNeoGreen","enableNeoHouseCalcPage","enableNeoInvestmentIdea","enableNeoMortgageCalcPage","enableNeoQSPReportsLeaf","enableNeoResearchReport","enableOffPeakArticleInBodyAds","enableOffPeakPortalAds","enableOffPeakDockAds","enablePersonalFinanceArticleReadMoreAlgo","enablePersonalFinanceNavBar","enablePersonalFinanceNewsletterIntegration","enablePersonalFinanceZillowIntegration","enablePfPremium","enablePfStreaming","enablePinholeScreenshotOGForQuote","enablePlus","enablePortalStockStory","enablePrivateCompany","enablePrivateCompanySurvey","enableQSP1PNews","enableQSPChartEarnings","enableQSPChartNewShading","enableQSPChartRangeTooltips","enableQSPEarnings","enableQSPEarningsVsRev","enableQSPHistoryPlusDownload","enableQSPLiveEarnings","enableQSPLiveEarningsCache","enableQSPLiveEarningsFeatureCue","enableQSPHoldingsCard","enableQSPNavIcon","enableQuoteLookup","enableRecentQuotes","enableResearchHub","enableScreenerCustomColumns","enableScreenerHeatMap","enableScreenersCollapseDock","enableSECFiling","enableSigninBeforeCheckout","enableSmartAssetMsgA","enableStockStoryPfPage","enableStockStoryTimeToBuy","enableStreamOnlyNews","enableTradeNow","enableYPFArticleReadMoreAll","enableVideoInHero","enableDockQuoteEventsModule","enablePfDetailDockCollapse","enablePfPrivateCompany","enableHoneyLinks","enableFollowedLatestNews","enableCGFollowedLatestNews","enableDockModuleDescriptions","fes_1003_silver-evergreen","fes_1004_silver-portfolios","enableCompareFeatures","enableGenericHeatMap","enableQSPIndustryHeatmap","enableStatusBadge"],"isDebug":false,"isForScreenshot":false,"isWebview":false,"theme":"auto","pnrID":"","isError":false,"gucJurisdiction":"ID","areAdsEnabled":true,"ccpa":{"warning":"","footerSequence":["terms_and_privacy","dashboard"],"links":{"dashboard":{"url":"https://guce.yahoo.com/privacy-dashboard?locale=en-US","label":"Privacy Dashboard","id":"privacy-link-dashboard"},"terms_and_privacy":{"multiurl":true,"label":"${terms_link}Terms${end_link} and ${privacy_link}Privacy Policy${end_link}","urls":{"terms_link":"https://guce.yahoo.com/terms?locale=en-US","privacy_link":"https://guce.yahoo.com/privacy-policy?locale=en-US"},"ids":{"terms_link":"privacy-link-terms-link","privacy_link":"privacy-link-privacy-link"}}}},"yrid":"1e112f1k3giu3","user":{"age":-2147483648,"crumb":"2UpwJ21ULi0","firstName":null,"gender":"","year":0}}}'
    headers = {
        "origin": "https://finance.yahoo.com",
        "Content-Type": "text/plain",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()

        try:
            json_data = response.json()
            if not json_data.get("data"):
                raise KeyError("No 'data' key found in response")
            return json_data

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON response: {str(e)}", e.doc, e.pos)

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 404:
            raise requests.exceptions.HTTPError(
                f"Stock symbol '{stock_symbol}' not found"
            )
        elif status_code == 429:
            raise requests.exceptions.HTTPError(
                "Rate limit exceeded. Please try again later"
            )
        else:
            raise requests.exceptions.HTTPError(f"HTTP error occurred: {str(e)}")

    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError(
            "Failed to connect to Yahoo Finance. Please check your internet connection"
        )

    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout(
            "Request timed out while fetching data from Yahoo Finance"
        )

    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"An error occurred while fetching data: {str(e)}"
        )


if __name__ == "__main__":
    # print(yahoo_finance_news_tool.invoke("RELIANCE.NS"))
    # print(duckduckgo_news_search_tool.invoke("RELIANCE.NS"))
    print(fetch_finance_news("RELIANCE.NS"))
