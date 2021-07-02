from flask import Flask, jsonify
from google.cloud import bigquery


app = Flask(__name__)


bigquery_client = bigquery.Client()


def get_definition_requests_per_day():
    return bigquery_client.query('SELECT DATE(time) as d, COUNT(time) as cnt FROM analytics.definition_requests GROUP BY d ORDER BY d').result()


def row_to_dict(row):
    return {k: v for k, v in row.items()}


@app.route('/definition_requests_per_day')
def requests_per_day():
    rows = []
    for row in get_definition_requests_per_day():
        rows.append(row_to_dict(row))
    response = jsonify(rows)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/total_definition_requests')
def total_requests():
    results = get_definition_requests_per_day()
    rows = []
    total = 0
    for row in results:
        d = row_to_dict(row)
        total += d['cnt']
        d['cnt'] = total
        rows.append(d)
    response = jsonify(rows)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == '__main__':
    app.run('localhost')
