# PageSpeed Insights Checker

Checks urls in [PageSpeed Insights](https://developers.google.com/speed/pagespeed/insights), generate small report and send it to Slack.

## Requirements
- Python (deps: `requests`)

## Usage
```bash
pip install -r requirements.txt

# unneccessary - if you want to use own Google API Key (instead of anonymous)
export GOOGLE_API_KEY='GOOGLE_API_KEY'

# if you want to get notifications to Slack - set this variables
export SLACK_INCOMING_KEY='T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
export SLACK_CHANNEL='SLACK_CHANNEL' # e.g. '#general' or '@someone'

export STATE_FILE='file.json' # will be used to restore/save state between runs

python main.py https://google.com https://stackoverflow.com/ https://github.com/
```
