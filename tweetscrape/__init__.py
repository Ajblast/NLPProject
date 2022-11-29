from time import sleep

import pandas as pd
import requests

class UserAgents:
    v2FullArchiveSearchPython = 'v2FullArchiveSearchPython'
    v2TweetLookupPython = 'v2TweetLookupPython'
    v2RecentSearchPython = 'v2RecentSearchPython'

    user_agent_url_map = {
        'https://api.twitter.com/2/tweets/search/all': v2FullArchiveSearchPython,
        'https://api.twitter.com/1.1/search/tweets.json': '',
        'https://api.twitter.com/2/tweets/search/recent': v2RecentSearchPython,
    }

class ScraperSimple:
    def __init__(self, bearer_oauth_token, search_url='https://api.twitter.com/2/tweets/search/all', user_agent=None):
        """Initialize ScraperSimple

        Args:
            bearer_oauth_token (str): Twitter-issued bearer OAuth token.
            search_url (str, optional): The endpoint to query. Defaults to 'https://api.twitter.com/2/tweets/search/all'.
            user_agent (str, optional): A specific user agent string.  Defaults to None. The class will attempt to assign the appropriate one if this is not specified.
        """
        self.request_headers = {}
        self.search_url = search_url
        self.bearer_oauth_token = bearer_oauth_token
        
        if user_agent == None:
            try: self.user_agent = UserAgents.user_agent_url_map[search_url]
            except: self.user_agent = ''
        else:
            self.user_agent = user_agent

    def bearer_oauth(self, r):
        r.headers['Authorization'] = f"Bearer {self.bearer_oauth_token}"
        r.headers['User-Agent'] = self.user_agent
        return r

    def fetch_tweets(self, params):
        resp = requests.get(self.search_url, auth=self.bearer_oauth, params=params)
        if not resp.status_code == 200:
            if resp.status_code == 503:
                sleep(200)
                resp = self.fetch_tweets(params)
            else:
                raise Exception(resp.status_code, resp.text)
        return resp.json()

    def scrape_super(self, params):
        json_resp = self.fetch_tweets(params)
        return json_resp # Will change later. Just need to play with the output now.


class ScraperPopular(ScraperSimple):
    def __init__(self, bearer_oauth_token):
        super().__init__(bearer_oauth_token, search_url='https://api.twitter.com/1.1/search/tweets.json')
        self.params = {
            'q': '',
            'lang': '',
            'max_results': '100',
            'tweet.fields': 'id,text,author_id,in_reply_to_user_id,geo,conversation_id,created_at,lang,public_metrics,referenced_tweets,reply_settings,source', 
            'user.fields': 'id,name,username,created_at,description,public_metrics,verified',
            'place.fields': 'full_name,id,country,country_code,geo,name,place_type', 
            'result_type': 'popular'
        }

    def set_pagination_token(self, token):
        self.params['max_id'] = token

    def get_pagination_token(self):
        return self.params['max_id']

    def scrape(self, query, max_results=500, lang=None, pagination_token=''):
        """Scrapes the endpoint https://api.twitter.com/1.1/search/tweets.json with the 'popular' `result_type` parameter.
        Loops until the number of tweets captured reaches max_results or until no remaining tweets are retrieved.

        Args:
            query (str): Your search query. Can be boolean, e.g., "('elon musk OR chief twit')"
            max_results (int, optional): The max number of rows you want in the returned DataFrame. Defaults to 500.
            lang (str, optional): ISO2 language code. None will remove the lang parameter. Defaults to None.
            pagination_token (str, optional): Really max_id for this endpoint. Used to set the 'max_id' param. Defaults to ''.

        Returns:
            pandas.DataFrame: A DataFrame of the results.
        """
        self.params['q'] = query
        self.params['max_results'] = str(max_results)

        if lang == None:
            try: self.params.pop('lang')
            except: pass
        else:
            self.params['lang'] = lang

        if not pagination_token == '':
            self.params['max_id'] = pagination_token

        dataframes = []
        out_of_tweets = False
        total_tweets = 0
        while (total_tweets < max_results) and (out_of_tweets == False):
            print("Fetching batch..")
            tweets = self.scrape_super(self.params)
            num_tweets = len(tweets['statuses'])
            print(f"> Fetched {num_tweets} tweets.", flush=True)
            total_tweets += num_tweets
            if num_tweets == 0: out_of_tweets = True
            try:
                self.params['max_id'] = tweets['search_metadata']['next_results'].split('?')[1].split('=')[1].split('&')[0]
            except:
                df = pd.DataFrame(tweets['statuses'])
                dataframes.append(df)
                print("Out of tweets..")
                out_of_tweets = True

            df = pd.DataFrame(tweets['statuses'])
            dataframes.append(df)
            sleep(3)

        print(f"------ Total fetched: {total_tweets} ------", flush=True)
        return pd.concat(dataframes, ignore_index=True)


class ScraperArchive(ScraperSimple):
    def __init__(self, bearer_oauth_token):
        super().__init__(bearer_oauth_token, search_url='https://api.twitter.com/2/tweets/search/all')
        self.params = {
            'query': '',
            'max_results': '',
            'tweet.fields': 'id,text,author_id,in_reply_to_user_id,geo,conversation_id,created_at,lang,public_metrics,referenced_tweets,reply_settings,source', 
            'user.fields': 'id,name,username,created_at,description,public_metrics,verified',
            'place.fields': 'full_name,id,country,country_code,geo,name,place_type'
        }

    def set_pagination_token(self, token):
        self.params['pagination_token'] = token

    def get_pagination_token(self):
        return self.params['pagination_token']

    def scrape(self, query, max_results=500, lang=None, pagination_token=''):
        """Scrapes the endpoint https://api.twitter.com/1.1/search/tweets.json with the 'popular' `result_type` parameter.
        Loops until the number of tweets captured reaches max_results or until no remaining tweets are retrieved.

        Args:
            query (str): Your search query. Can be boolean, e.g., "('elon musk OR chief twit')"
            max_results (int, optional): The max number of rows you want in the returned DataFrame. Defaults to 500.
            lang (str, optional): ISO2 language code for the tweets. None will disclude the lang argument. Defaults to None.
            pagination_token (str, optional): Used to set the 'pagination_token' param. Defaults to ''.

        Returns:
            pandas.DataFrame: A DataFrame of the results.
        """
        if lang == None:
            self.params['query'] = query
        else:
            self.params['query'] = f"{query} lang:{lang}"

        if max_results < 501: # Lets user specify max > 500 and it will keep looping getting 100 tweets/time
            self.params['max_results'] = str(max_results)
        else:
            self.params['max_results'] = '100'

        if not pagination_token == '':
            self.params['pagination_token'] = pagination_token
        
        dataframes = []
        out_of_tweets = False
        total_tweets = 0
        while (total_tweets < max_results) and (out_of_tweets == False):
            print("Fetching batch..")
            tweets = self.scrape_super(self.params)
            num_tweets = len(tweets['data'])
            print(f"> Fetched {num_tweets} tweets.", flush=True)
            total_tweets += num_tweets
            
            if num_tweets == 0: out_of_tweets = True
            try:
                self.params['pagination_token'] = tweets['meta']['next_token']
            except:
                df = pd.DataFrame(tweets['data'])
                dataframes.append(df)
                print("Out of tweets...")
                out_of_tweets = True

            df = pd.DataFrame(tweets['data'])
            dataframes.append(df)
            sleep(3)

        print(f"------ Total fetched: {total_tweets} ------", flush=True)
        return pd.concat(dataframes, ignore_index=True)
