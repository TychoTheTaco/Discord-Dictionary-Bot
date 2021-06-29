'use strict';

const API_ROOT = 'http://localhost:3000/'

Chart.defaults.plugins.legend.display = false
Chart.defaults.responsive = false;
Chart.defaults.plugins.title.display = true;
Chart.defaults.color = 'whitesmoke';
Chart.defaults.animation = false;

fetch(API_ROOT + 'requests-per-day').then(
    (response) => {
        console.log(response);
        response.json().then(
            (data) => {

                let xValues = [];
                let yValues = [];

                let date = new Date(Object.keys(data)[0]);
                const today = new Date();
                while (date.getUTCDate() !== today.getUTCDate() || date.getUTCMonth() !== today.getUTCMonth() || date.getUTCFullYear() !== today.getUTCFullYear()){
                    const key = (date.getMonth() + 1) + "-" + date.getDate() + "-" + date.getFullYear();
                    xValues.push(key);
                    if (key in data){
                        yValues.push(data[key])
                    }  else {
                        yValues.push(0);
                    }
                    date.setUTCDate(date.getUTCDate() + 1);
                }

                const daily_requests_container = document.getElementById('daily_requests_container');
                daily_requests_container.innerHTML += `Minimum: ${Math.min(...yValues)}<br>Maximum: ${Math.max(...yValues)}<br>Average: ${Math.round(yValues.reduce((a, b) => a + b) / yValues.length)}`

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
                            scales:  {
                                x: {
                                    ticks: {
                                        maxTicksLimit: 3,
                                        maxRotation: 0
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
            },
            (reason) => {
                console.log(reason);
            }
        );
    },
    (reason) => {
        console.log(reason);
    }
);

fetch(API_ROOT + 'requests-per-day').then(
    (response) => {
        response.json().then(
            (data) => {
                console.log(data);

                let xValues = [];
                let yValues = [];

                let date = new Date(Object.keys(data)[0]);
                const today = new Date();
                let sum = 0;
                while (date.getUTCDate() !== today.getUTCDate() || date.getUTCMonth() !== today.getUTCMonth() || date.getUTCFullYear() !== today.getUTCFullYear()){
                    const key = (date.getMonth() + 1) + "-" + date.getDate() + "-" + date.getFullYear();
                    xValues.push(key);
                    if (key in data){
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
);

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
                while (date.getUTCDate() !== today.getUTCDate() || date.getUTCMonth() !== today.getUTCMonth() || date.getUTCFullYear() !== today.getUTCFullYear()){
                    const key = (date.getMonth() + 1) + "-" + date.getDate() + "-" + date.getFullYear();
                    xValues.push(key);
                    if (key in data){
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
);
