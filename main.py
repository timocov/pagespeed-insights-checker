import os
import sys
import requests


PAGESPEED_API_URL = 'https://www.googleapis.com/pagespeedonline/v2/runPagespeed'
PAGESPEED_URL = 'https://developers.google.com/speed/pagespeed/insights/'
SLACK_API_URL = 'https://hooks.slack.com/services/'

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)
SLACK_INCOMING_KEY = os.environ.get('SLACK_INCOMING_KEY', None)
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', None)

class WrongResponseCode(Exception):
    def __init__(self, code):
        self._code = code

    def __str__(self):
        return 'Page returns {0} code'.format(self._code)


def request_score_for_strategy(url, strategy):
    params = {
        'url': url,
        'strategy': strategy
    }

    if GOOGLE_API_KEY is not None:
        params['key'] = GOOGLE_API_KEY

    response = requests.get(PAGESPEED_API_URL, params)
    response.raise_for_status()
    report = response.json()
    if report.get('errors', None) is not None:
        error = report.get('errors')
        raise Exception(error.get('message'))

    page_response_code = report.get('responseCode')
    if page_response_code < 200 or page_response_code > 399:
        raise WrongResponseCode(page_response_code)

    return report.get('ruleGroups', {}).get('SPEED', {}).get('score', -1)


def request_scores(url):
    return {
        'mobile': request_score_for_strategy(url, 'mobile'),
        'desktop': request_score_for_strategy(url, 'desktop'),
    }


def send_to_slack(message):
    if SLACK_INCOMING_KEY is None or SLACK_CHANNEL is None:
        print('Skip send message to Slack because of empty incoming key or channel')
        return

    json_data = {
        'text': message,
        'channel': SLACK_CHANNEL,
        'username': 'pagespeed-insights',
        'icon_emoji': ':traffic_light:',
    }

    response = requests.post('{0}/{1}'.format(SLACK_API_URL, SLACK_INCOMING_KEY), json=json_data)
    response.raise_for_status()
    print('Slack response: {0}'.format(response.content))


def main():
    urls = sys.argv[1:]
    assert len(urls) > 0, 'Urls must be specified'
    print('Generating report for pages: {0}\n'.format(', '.join(urls)))

    message = ['*PageSpeed Insights* report:']

    for url in urls:
        print('Generate report for {0}'.format(url))
        report_string = None
        try:
            scores = request_scores(url)
            report_string = ':computer: - *{desktop}*/100 :iphone: - *{mobile}*/100'.format(**scores)
        except WrongResponseCode as error:
            report_string = '`{0}` :bangbang:'.format(error)

        print('  Scores: {0}'.format(report_string))
        message.append('<{0}?url={1}|{1}> {2}'.format(PAGESPEED_URL, url, report_string))

    send_to_slack('\n'.join(message))


if __name__ == '__main__':
    main()
