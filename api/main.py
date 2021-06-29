from flask import Flask
from google.cloud import bigquery


app = Flask(__name__)


bigquery_client = bigquery.Client()


@app.route('/requests')
def requests():
    results = bigquery_client.query('SELECT COUNT(DISTINCT(channel_id)) AS uniqueChannels FROM analytics.definition_requests').result()
    rows = []
    for row in results:
        rows.append([x for x in row.items()])
    return {'rows': rows}


@app.route('/dictionary_api_requests')
def dictionary_api_requests():
    return {}


@app.route('/commands')
def commands():
    return {}


if __name__ == '__main__':
    app.run('localhost')
