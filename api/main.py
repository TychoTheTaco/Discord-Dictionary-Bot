import datetime

from flask import Flask, jsonify
from google.cloud import bigquery


app = Flask(__name__)


bigquery_client = bigquery.Client()


def get_definition_requests_per_day():
    return bigquery_client.query('SELECT DATE(time) as d, COUNT(time) as cnt FROM analytics.definition_requests GROUP BY d ORDER BY d').result()


def row_to_dict(row):
    return {k: v for k, v in row.items()}


def get_days_in_range(start: datetime.datetime, end: datetime.datetime) -> [datetime.date]:
    days = []

    # Align start and end to start of day
    start = datetime.date(start.year, start.month, start.day)
    end = datetime.date(end.year, end.month, end.day)

    while start <= end:
        days.append(start)
        start += datetime.timedelta(days=1)

    return days


@app.route('/definition_requests')
def definition_requests_per_day():
    query = 'SELECT period, SUM(cnt) AS cnt FROM (' \
            'SELECT DATE(time) as period, COUNT(time) AS cnt FROM analytics.definition_requests GROUP BY period ' \
            'UNION ALL ' \
            'SELECT period, 0 FROM UNNEST(GENERATE_DATE_ARRAY(DATE("2021-1-1"), current_date())) period' \
            ') GROUP BY period ORDER BY period'
    rows = []
    for row in bigquery_client.query(query):
        rows.append(row_to_dict(row))
    response = jsonify(rows)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/total_definition_requests')
def total_definition_requests():
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


@app.route('/commands_per_day')
def commands_per_day():

    # Get unique commands
    command_names = [row.get('command_name') for row in bigquery_client.query('SELECT DISTINCT command_name FROM analytics.commands').result()]
    print(command_names)
    command_names = filter(lambda item: item not in ['list', 'set', 'voices', 'languages', 'property'], command_names)

    # Find commands per day for each command
    result = {}
    for command_name in command_names:
        # Get all days since beginning
        usage = {date: {'text_count': 0, 'slash_count': 0} for date in get_days_in_range(datetime.datetime(2021, 1, 1), datetime.datetime.today())}
        query = 'SELECT DATE(time) as d, COUNTIF(NOT is_slash) as cnt, COUNTIF(is_slash) as slash_cnt FROM analytics.commands WHERE command_name = @command_name GROUP BY d ORDER BY d'
        job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('command_name', "STRING", command_name)])
        for row in bigquery_client.query(query, job_config=job_config).result():
            d = row_to_dict(row)
            usage[d['d']]['text_count'] = d['cnt']
            usage[d['d']]['slash_count'] = d['slash_cnt']
        result[command_name] = [{'date': date, **usage[date]} for date in usage.keys()]

    response = jsonify(result)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/text_vs_slash_commands')
def text_vs_slash_commands():
    result = {date: {'text_count': 0, 'slash_count': 0} for date in get_days_in_range(datetime.datetime(2021, 1, 1), datetime.datetime.today())}
    for row in bigquery_client.query('SELECT DATE(time) as d, COUNTIF(NOT is_slash) as cnt, COUNTIF(is_slash) as slash_cnt FROM analytics.commands GROUP BY d ORDER BY d').result():
        d = row_to_dict(row)
        result[d['d']]['text_count'] = d['cnt']
        result[d['d']]['slash_count'] = d['slash_cnt']
    result = [{'date': date, **result[date]} for date in result.keys()]

    response = jsonify(result)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/dictionary_api_usage')
def dictionary_api_usage():
    result = {}
    for row in bigquery_client.query('SELECT api_name, COUNT(api_name) as cnt FROM `analytics.dictionary_api_requests` GROUP BY api_name').result():
        d = row_to_dict(row)
        result[d['api_name']] = d['cnt']

    response = jsonify(result)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


if __name__ == '__main__':
    app.run('localhost')
