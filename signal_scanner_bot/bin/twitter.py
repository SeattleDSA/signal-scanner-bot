from signal_scanner_bot import twitter


api = twitter.get_api()
api.update_status("TESTING: hello world")
