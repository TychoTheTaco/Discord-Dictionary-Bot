'use strict';

const API_ROOT = 'https://formal-scout-290305.wl.r.appspot.com/'

Chart.defaults.plugins.legend.display = false
Chart.defaults.responsive = false;
Chart.defaults.plugins.title.display = true;
Chart.defaults.color = 'whitesmoke';
Chart.defaults.animation = false;

class Graph {

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

        const daily_requests_container = document.getElementById('daily_requests_container');
        daily_requests_container.innerHTML += `Maximum: ${Math.max(...yValues)}<br>Average: ${Math.round(yValues.reduce((a, b) => a + b) / yValues.length)}`

        const ctx = document.getElementById('requests_per_day_canvas').getContext('2d');
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
                            text: 'Daily Requests'
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

        const daily_requests_container = document.getElementById('total_requests_container');
        daily_requests_container.innerHTML += `<br>Maximum: ${Math.max(...yValues)}`

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
                            text: 'Total Requests'
                        }
                    }
                }
            }
        );
    }

}

const graphs = [new RequestsPerDayGraph(), new TotalRequestsPerDayGraph()];

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
