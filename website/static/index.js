'use strict';

const API_ROOT = 'https://formal-scout-290305.wl.r.appspot.com/'

Chart.defaults.plugins.legend.display = false
Chart.defaults.responsive = false;
Chart.defaults.plugins.title.display = true;
Chart.defaults.color = 'whitesmoke';
Chart.defaults.animation = false;

const COMMAND_COLORS = {
    'define': '#C62828',
    'befine': '#880E4F',
    'help': '#F57F17',
    'stop': '#FF6F00',
    'voices': '#827717',
    'property': '#03A9F4',
    'stats': '#8BC34A',
    'languages': '#006064',
}

const DICTIONARY_API_COLORS = {
    'unofficial_google': '#D32F2F',
    'owlbot': '#1976D2',
    'merriam_webster_collegiate': '#388E3C',
    'merriam_webster_medical': '#FBC02D',
    'rapid_words': '#F57C00'
}

class Graph {

    constructor(container) {
        this.container = container;
        this.canvas = this.container.shadowRoot.querySelector('canvas');
    }

    async load() {
        throw Error('Abstract method not implemented!');
    }

}

class RequestsPerDayGraph extends Graph {

    async load() {
        const response = await (await fetch(API_ROOT + 'definition_requests_per_day')).json();

        let items = [];

        // Add missing days
        const today = new Date();
        let date = new Date(response[0]['d']);
        let i = 0;
        while (date < today) {
            if (i < response.length && new Date(response[i]['d']).getTime() === date.getTime()) {
                const item = response[i];
                item['date'] = new Date(date);
                items.push(item);
                ++i;
            } else {
                items.push({'date': new Date(date), 'cnt': 0});
            }
            date.setUTCDate(date.getUTCDate() + 1);
        }

        let xValues = [];
        let yValues = [];

        for (const item of items) {
            xValues.push(item['date']);
            yValues.push(item['cnt']);
        }

        const daily_requests_container = this.container;
        daily_requests_container.innerHTML += `Maximum: ${Math.max(...yValues)}<br>Average: ${Math.round(yValues.reduce((a, b) => a + b) / yValues.length)}`

        const ctx = this.canvas.getContext('2d');
        const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: xValues,
                    datasets: [{
                        data: yValues,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        pointRadius: 0
                    }]
                },
                options: {
                    scales: {
                        x: {
                            ticks: {
                                autoSkip: false,
                                maxRotation: 0,
                                callback: function (value, index, values) {
                                    if (xValues[index].getDate() !== 1) {
                                        return null;
                                    }
                                    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                                    return monthNames[xValues[index].getMonth()];
                                }
                            }
                        }
                    },
                    plugins: {
                        title: {
                            text: 'Daily Definition Requests'
                        }
                    }
                }
            }
        );
    }

}

class TotalRequestsPerDayGraph extends Graph {

    async load() {
        const response = await (await fetch(API_ROOT + 'definition_requests_per_day')).json();

        let items = [];

        // Add missing days
        const today = new Date();
        let date = new Date(response[0]['d']);
        let i = 0;
        while (date < today) {
            if (i < response.length && new Date(response[i]['d']).getTime() === date.getTime()) {
                const item = response[i];
                item['date'] = new Date(date);
                items.push(item);
                ++i;
            } else {
                items.push({'date': new Date(date), 'cnt': 0});
            }
            date.setUTCDate(date.getUTCDate() + 1);
        }

        let xValues = [];
        let yValues = [];

        let sum = 0;
        for (const item of items) {
            xValues.push(item['date']);
            sum += item['cnt'];
            yValues.push(sum);
        }

        const daily_requests_container = this.container;
        daily_requests_container.innerHTML += `<br>Maximum: ${Math.max(...yValues)}`

        const ctx = this.canvas.getContext('2d');
        const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: xValues,
                    datasets: [{
                        data: yValues,
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1,
                        pointRadius: 0
                    }]
                },
                options: {
                    scales: {
                        x: {
                            ticks: {
                                autoSkip: false,
                                maxRotation: 0,
                                callback: function (value, index, values) {
                                    if (xValues[index].getDate() !== 1) {
                                        return null;
                                    }
                                    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
                                    return monthNames[xValues[index].getMonth()];
                                }
                            }
                        }
                    },
                    plugins: {
                        title: {
                            text: 'Total Definition Requests'
                        }
                    }
                }
            }
        );
    }
}

class CommandsPerDay extends Graph {

    async load() {
        const response = await (await fetch(API_ROOT + 'commands_per_day')).json();

        const datasets = [];

        for (const commandName in response) {
            const items = response[commandName];

            let text_count_sum = 0;
            let slash_count_sum = 0;
            for (const item of items) {
                text_count_sum += item['text_count'];
                slash_count_sum += item['slash_count'];
            }
            datasets.push({
                'label': commandName,
                'data': text_count_sum + slash_count_sum
            })
        }

        datasets.sort((a, b) => {
            return b['data'] - a['data'];
        })

        const labels = []
        const datas = [];
        const colors = [];
        for (const d of datasets) {
            labels.push(d['label']);
            datas.push(d['data']);
            colors.push(COMMAND_COLORS[d['label']]);
        }

        const ctx = this.canvas.getContext('2d');
        const chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            data: datas,
                            backgroundColor: colors
                        }
                    ]
                },
                options: {
                    indexAxis: 'y',
                    plugins: {
                        title: {
                            text: 'Commands'
                        },
                        datalabels: {
                            formatter: function (value, context) {
                                return context.chart.data.labels[context.dataIndex];
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'logarithmic',
                            ticks: {
                                callback: (value, index, values) => {
                                    console.log(value, Math.log10(value));
                                    if (Math.log10(value) % 1 === 0){
                                        return Math.floor(value);
                                    }
                                    if (index === values.length - 1){
                                        console.log('LAST:' + Math.pow(10, Math.ceil(Math.log10(value))));
                                        return Math.pow(10, Math.ceil(Math.log10(value)));
                                    }
                                    return null;
                                }
                            },
                            afterBuildTicks: (axis) => {
                                //TODO: This is to force a tick at 10,000 but this seems like a bad way of doing it. ticks.min and max arent working
                                axis.ticks.push({
                                    value: 10000, major: true, label: ""
                                });
                            }
                        }
                    }
                }
            }
        );
    }

}

class TextVsSlashCommands extends Graph {

    async load() {
        const response = await (await fetch(API_ROOT + 'text_vs_slash_commands')).json();

        let text_count_sum = 0;
        let slash_count_sum = 0;
        for (const item of response) {
            text_count_sum += item['text_count'];
            slash_count_sum += item['slash_count'];
        }

        const ctx = this.canvas.getContext('2d');
        const chart = new Chart(ctx, {
                plugins: [ChartDataLabels],
                type: 'pie',
                data: {
                    labels: ['Text', 'Slash'],
                    datasets: [
                        {
                            data: [text_count_sum, slash_count_sum],
                            backgroundColor: ['#BA2944', '#354CBA']
                        }
                    ]
                },
                options: {
                    plugins: {
                        title: {
                            text: 'Text vs Slash Commands'
                        },
                        datalabels: {
                            formatter: function (value, context) {
                                return context.chart.data.labels[context.dataIndex];
                            }
                        }
                    }
                }
            }
        );
    }

}

class DictionaryApiUsage extends Graph {

    async load() {
        const response = await (await fetch(API_ROOT + 'dictionary_api_usage')).json();

        const labels = [];
        const counts = []
        const colors = [];
        for (const item in response) {
            labels.push(item)
            counts.push(response[item])
            colors.push(DICTIONARY_API_COLORS[item])
        }

        const ctx = this.canvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'pie',
            plugins: [ChartDataLabels],
            data: {
                labels: labels,
                datasets: [
                    {
                        data: counts,
                        backgroundColor: colors
                    }
                ]
            },
            options: {
                plugins: {
                    title: {
                        text: 'Dictionary API Usage'
                    },
                    datalabels: {
                        formatter: function (value, context) {
                            return context.chart.data.labels[context.dataIndex];
                        }
                    }
                }
            }
        });
    }

}

customElements.define('chart-container', class extends HTMLElement {

    constructor() {
        super();
        const template = document.getElementById('chart_container_template');
        this.attachShadow({mode: 'open'}).appendChild(template.content.cloneNode(true));
    }

    connectedCallback() {

    }

});

function createNewChartContainer() {
    const main_container = document.getElementById('main_content');
    const child = document.createElement('chart-container');
    main_container.appendChild(child);
    return child;
}

const graphs = [
    new RequestsPerDayGraph(createNewChartContainer()),
    new TotalRequestsPerDayGraph(createNewChartContainer()),
    new CommandsPerDay(createNewChartContainer()),
    new TextVsSlashCommands(createNewChartContainer()),
    new DictionaryApiUsage(createNewChartContainer())
];

(async () => {
    const promises = [];
    graphs.forEach((graph) => {
        promises.push(graph.load());
    })
    await Promise.all(promises);
})().catch((error) => {
    console.log(error);
});

/*

fetch(API_ROOT + 'active-guilds').then(
    (response) => {
        response.json().then(
            (data) => {
                console.log(data);

                let xValues = [];
                let yValues = [];

                let date = new Date(Object.keys(data)[0]);
                const today = new Date();
                let sum = 0;
                while (date.getUTCDate() !== today.getUTCDate() || date.getUTCMonth() !== today.getUTCMonth() || date.getUTCFullYear() !== today.getUTCFullYear()) {
                    const key = (date.getMonth() + 1) + "-" + date.getDate() + "-" + date.getFullYear();
                    xValues.push(key);
                    if (key in data) {
                        sum += data[key];
                    }
                    yValues.push(sum);
                    date.setUTCDate(date.getUTCDate() + 1);
                }

                const ctx = document.getElementById('total_requests_canvas').getContext('2d');
                const chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: xValues,
                            datasets: [{
                                data: yValues,
                                borderColor: 'rgb(75, 192, 192)',
                                tension: 0.1,
                                pointRadius: 0
                            }]
                        },
                        options: {
                            plugins: {
                                title: {
                                    text: 'Total Requests'
                                }
                            }
                        }
                    }
                );
            },
            (reason) => {
                console.log(reason);
            }
        );
    },
    (reason) => {
        console.log(reason);
    }
);*/
