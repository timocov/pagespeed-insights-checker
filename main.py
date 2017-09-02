import os
import json
import sys
import requests


PAGESPEED_API_URL = 'https://www.googleapis.com/pagespeedonline/v2/runPagespeed'
PAGESPEED_URL = 'https://developers.google.com/speed/pagespeed/insights/'
SLACK_API_URL = 'https://hooks.slack.com/services/'

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', None)
SLACK_INCOMING_KEY = os.environ.get('SLACK_INCOMING_KEY', None)
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', None)
STATE_FILE = os.environ.get('STATE_FILE', None)


class WrongResponseCode(Exception):
    def __init__(self, code):
        Exception.__init__(self)
        self.code = code


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


def generate_pagespeed_slack_url(page_url):
    return '<{0}?url={1}|{1}>'.format(PAGESPEED_URL, page_url)


def generate_scores_slack_message(scores, changes):
    desktop_str = ':computer: - *{desktop}*/100 ({desktop_change:+})'.format(**scores, **changes)
    mobile_str = ':iphone: - *{mobile}*/100 ({mobile_change:+})'.format(**scores, **changes)
    return '{0} {1}'.format(desktop_str, mobile_str)


def get_changes(prev_scores, new_scores):
    # prev state might be empty but not new
    desktop_change = new_scores.get('desktop') - prev_scores.get('desktop', 0)
    mobile_change = new_scores.get('mobile') - prev_scores.get('mobile', 0)

    if desktop_change == 0 and mobile_change == 0:
        return None

    return {
        'desktop_change': desktop_change,
        'mobile_change': mobile_change,
    }


def load_prev_state():
    if STATE_FILE is not None and os.path.exists(STATE_FILE):
        with open(STATE_FILE) as file:
            return json.load(file)
    return {}


def save_state(new_state):
    if STATE_FILE is None:
        print('Cannot save state - you must specify state file')
        return

    with open(STATE_FILE, 'w') as file:
        file.write(json.dumps(new_state))

    print('State saved to file "{0}"'.format(STATE_FILE))


def main():
    urls = sys.argv[1:]
    assert len(urls) > 0, 'Urls must be specified'
    print('Generating report for pages: {0}'.format(', '.join(urls)))

    prev_state = load_prev_state()
    print('Used saved state: {0}'.format(json.dumps(prev_state)))

    new_state = prev_state.copy()
    need_send_message_to_slack = False

    slack_message_parts = ['*PageSpeed Insights* report:']
    for url in urls:
        print('Generating report for {0}'.format(url))

        page_report_str = None
        try:
            scores = request_scores(url)
            changes = get_changes(prev_state.get(url, {}), scores)
            if changes is None:
                print('  Scores for page is not changed')
                continue

            new_state[url] = scores
            page_report_str = generate_scores_slack_message(scores, changes)
            print('  Desktop={desktop}/100 ({desktop_change:+}), mobile={mobile}/100 ({mobile_change:+})'.format(**scores, **changes))
        except WrongResponseCode as error:
            page_report_str = '`Page returns {0}` :bangbang:'.format(error.code)
            print('  Cannot generate report - page returns {0} code'.format(error.code))

        need_send_message_to_slack = True
        pagespeed_link = generate_pagespeed_slack_url(url)
        slack_message_parts.append('{0} {1}'.format(pagespeed_link, page_report_str))

    save_state(new_state)
    if need_send_message_to_slack:
        send_to_slack('\n'.join(slack_message_parts))
    else:
        print('Skip sending message to slack because of no changes for all pages')


if __name__ == '__main__':
    main()
