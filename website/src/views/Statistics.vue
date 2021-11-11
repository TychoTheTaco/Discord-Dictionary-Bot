<template>

	<div ref="main_content" style="display: flex; flex-direction: row; justify-content: center; flex-wrap: wrap;">
		<Graph ref="a"/>
		<Graph ref="b"/>
		<Graph ref="c"/>
		<Graph ref="d"/>
	</div>

</template>

<script>
import Graph from "@/components/Graph";

import {Chart, registerables} from "chart.js";

Chart.register(...registerables);
import ChartDataLabels from 'chartjs-plugin-datalabels';

const API_ROOT = 'https://formal-scout-290305.wl.r.appspot.com/'

Chart.defaults.plugins.legend.display = false
Chart.defaults.maintainAspectRatio = false;
Chart.defaults.plugins.title.display = true;
Chart.defaults.color = 'whitesmoke';
Chart.defaults.animation = false;

const COMMAND_COLORS = {
	'define': '#BA2944',
	'help': '#1565C0',
	'stop': '#F9A825',
	'translate': '#2E7D32',
	'settings': '#AD1457',

	'befine': '#EF6C00',
	'stats': '#6A1B9A'
}

const DICTIONARY_API_COLORS = {
	'unofficial_google': '#BA2944',
	'owlbot': '#F9A825',
	'merriam_webster_collegiate': '#1565C0',
	'merriam_webster_medical': '#2E7D32',
	'rapid_words': '#6A1B9A'
}

const DICTIONARY_API_NAMES = {
	'unofficial_google': 'Unofficial Google',
	'owlbot': 'Owlbot',
	'merriam_webster_collegiate': 'Merriam Webster Collegiate',
	'merriam_webster_medical': 'Merriam Webster Medical',
	'rapid_words': 'Rapid Words'
}

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export default {
	name: 'Statistics',
	components: {
		Graph
	},
	mounted() {
		window.addEventListener('resize', this.onWindowResize);
		this.onWindowResize();

		this.$refs.a.load((async (container, canvas, stats) => {
			const response = await (await fetch(API_ROOT + 'definition_requests')).json();

			let xValues = [];
			let yValues = [];

			for (const item of response) {
				xValues.push(new Date(item['period']));
				yValues.push(item['cnt']);
			}

			const datasets = [];
			datasets.push({
				data: yValues,
				backgroundColor: 'rgb(75, 192, 192)',
				type: 'bar',
				label: 'Requests',
				order: 2
			})

			function movingAverage(period, items) {
				const averages = [];
				for (let i = 0; i < items.length; ++i) {
					const x = items.slice(i - period < 0 ? 0 : i - period, i + 1);
					const average = x.reduce((a, b) => a + b) / x.length;
					averages.push(Math.round(average));
				}
				return averages;
			}

			// Calculate 30-day average
			datasets.push({
				data: movingAverage(30, yValues),
				borderColor: '#BA2944',
				tension: 0.1,
				pointRadius: 0,
				type: 'line',
				label: '30 day average',
				order: 1
			})

			const ctx = canvas.getContext('2d');
			new Chart(ctx, {
					type: 'line',
					data: {
						labels: xValues,
						datasets: datasets
					},
					options: {
						scales: {
							x: {
								ticks: {
									autoSkip: false,
									maxRotation: 0,
									callback: function (value, index, values) {
										if (xValues[index].getUTCDate() !== 1) {
											return null;
										}
										return MONTH_NAMES[xValues[index].getUTCMonth()];
									}
								}
							}
						},
						plugins: {
							title: {
								text: 'Daily Definition Requests'
							},
							tooltip: {
								callbacks: {
									title: (context) => {
										const date = xValues[context[0].dataIndex];
										return MONTH_NAMES[date.getUTCMonth()] + " " + date.getUTCDate() + ", " + date.getUTCFullYear();
									}
								},
								intersect: false,
								mode: 'index'
							}
						}
					}
				}
			);
		}));

		this.$refs.b.load((async (container, canvas) => {
			const response = await (await fetch(API_ROOT + 'total_definition_requests')).json();

			let xValues = [];
			let yValues = [];

			for (const item of response) {
				xValues.push(new Date(item['period']));
				yValues.push(item['cnt']);
			}

			//container.innerHTML += `<br>Maximum: ${Math.max(...yValues)}`

			const ctx = canvas.getContext('2d');
			new Chart(ctx, {
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
										return MONTH_NAMES[xValues[index].getMonth()];
									}
								}
							}
						},
						plugins: {
							title: {
								text: 'Total Definition Requests'
							},
							tooltip: {
								callbacks: {
									title: (context) => {
										const date = xValues[context[0].dataIndex];
										return MONTH_NAMES[date.getUTCMonth()] + " " + date.getUTCDate() + ", " + date.getUTCFullYear();
									}
								},
								intersect: false,
								mode: 'index'
							}
						}
					}
				}
			);
		}));

		this.$refs.c.load((async (container, canvas) => {
			const response = await (await fetch(API_ROOT + 'command_usage')).json();

			const datasets = [];
			for (const item of response){
				datasets.push({
					'label': item['command_name'],
					'data': item['cnt']
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

			const ctx = canvas.getContext('2d');
			new Chart(ctx, {
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
										//console.log(value, Math.log10(value));
										if (Math.log10(value) % 1 === 0) {
											return Math.floor(value);
										}
										if (index === values.length - 1) {
											//console.log('LAST:' + Math.pow(10, Math.ceil(Math.log10(value))));
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
		}));

		this.$refs.d.load((async (container, canvas) => {
			const response = await (await fetch(API_ROOT + 'dictionary_api_usage')).json();

			const datas = [];

			for (const item in response) {
				datas.push({
					label: DICTIONARY_API_NAMES[item],
					count: response[item],
					color: DICTIONARY_API_COLORS[item]
				})
			}

			datas.sort((a, b) => {
				return b['count'] - a['count'];
			});

			const labels = [];
			const counts = []
			const colors = [];

			let total = 0;
			for (const item of datas) {
				labels.push(item['label'])
				counts.push(item['count'])
				colors.push(item['color'])
				total += item['count'];
			}

			const ctx = canvas.getContext('2d');
			new Chart(ctx, {
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
							text: 'Daily Dictionary API Usage'
						},
						legend: {
							display: true,
							position: 'right'
						},
						datalabels: {
							formatter: function (value, context) {
								return ((value / total) * 100).toFixed(1) + "%";
							}
						}
					}
				}
			});
		}));
	},
	unmounted() {
		window.removeEventListener('resize', this.onWindowResize);
	},
	methods: {
		onWindowResize() {
			this.$nextTick(() => {
				if (window.innerWidth < 700 || screen.availWidth < 700){
					this.$refs.main_content.style.flexDirection = 'column';
				} else {
					this.$refs.main_content.style.flexDirection = 'row';
				}
			});
		}
	}
}

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

</script>
