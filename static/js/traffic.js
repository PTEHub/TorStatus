// Initialize ECharts instance
var chart = echarts.init(document.getElementById('traffic-chart'));

// Format time to HH:mm:ss
function formatTime(date) {
    return date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
}

// Generate time points for the last 3 minutes (90 data points, one every 2 seconds)
function generateInitialTimes() {
    var times = [];
    var now = new Date();
    for (var i = 89; i >= 0; i--) {
        var pastTime = new Date(now - i * 2000); // One data point every 2 seconds
        times.push(formatTime(pastTime));
    }
    return times;
}

// Initial data: 90 data points, first 89 are 0
var initialData = Array(89).fill(0);
var initialTimes = generateInitialTimes();

// Chart configuration
var traffic_option = {
    backgroundColor: 'rgba(31, 31, 31, 0.3)',  // Dark background similar to Netdata
    title: {
        text: 'Network Traffic (Last 3 Minutes)',
        subtext: 'Upload (Red, Up) / Download (Blue, Down)',
        textStyle: {
            color: '#ffffff'  // Title color
        },
        subtextStyle: {
            color: '#aaaaaa'  // Subtitle color
        }
    },
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'cross'  // Show crosshair when cursor moves
        },
        formatter: function (params) {
            let content = params.map(item => {
                let value = Math.abs(item.value);
                let unit = 'KB/s';
                if (value >= 1024) {
                    value = (value / 1024).toFixed(2);
                    unit = 'MB/s';
                }
                return `${item.seriesName}: ${value} ${unit}`;
            }).join('<br/>');
            return `${params[0].name}<br/>${content}`;
        }
    },
    legend: {
        data: ['Upload', 'Download'],
        top: '5%',
        textStyle: {
            color: '#ffffff'  // Legend text color
        }
    },
    xAxis: {
        type: 'category',
        boundaryGap: false,
        data: initialTimes,
        axisLabel: {
            color: '#ffffff',  // X-axis label color
            formatter: function (value) {
                return value;  // Display formatted time
            }
        },
        axisLine: {
            lineStyle: {
                color: '#ffffff'  // X-axis line color
            }
        }
    },
    yAxis: {
        type: 'value',
        axisLabel: {
            color: '#ffffff',  // Y-axis label color
            formatter: function (value) {
                let absValue = Math.abs(value);
                if (absValue >= 1024) {
                    return (absValue / 1024).toFixed(2) + ' MB/s';
                }
                return absValue + ' KB/s';
            }
        },
        splitLine: {
            show: true,
            lineStyle: {
                color: '#444444',  // Grid line color
                type: 'dashed'
            }
        },
        axisLine: {
            lineStyle: {
                color: '#ffffff'  // Y-axis line color
            }
        },
        scale: true // Automatically adjust upper and lower limits
    },
    series: [
        {
            name: 'Upload',
            type: 'line',   // Regular line chart
            data: initialData.concat([0]),
            smooth: false,   // No smoothing
            showSymbol: false,  // Hide data point circles
            symbolSize: 8,       // Set circle size
            itemStyle: {
                color: '#e6194b'  // Red color for upload line
            },
            lineStyle: {
                color: '#e6194b',
                width: 0.75       // Set line thickness
            },
            areaStyle: {
                color: 'rgba(230, 25, 75, 0.3)'  // Red shadow
            }
        },
        {
            name: 'Download',
            type: 'line',   // Regular line chart
            data: initialData.concat([0]).map(v => -v),  // Invert data
            smooth: false,   // No smoothing
            showSymbol: false,  // Hide data point circles
            symbolSize: 8,       // Set circle size
            itemStyle: {
                color: '#3cb44b'  // Blue color for download line
            },
            lineStyle: {
                color: '#3cb44b',
                width: 0.75       // Set line thickness
            },
            areaStyle: {
                color: 'rgba(60, 180, 75, 0.3)'  // Blue shadow
            }
        }
    ]
};

chart.setOption(traffic_option);

// Update data
function updateData() {
    fetch('/data')
        .then(response => response.json())
        .then(data => {
            // Get current time
            var currentTime = formatTime(new Date());

            // Add new data point
            traffic_option.xAxis.data.push(currentTime);
            traffic_option.series[0].data.push(data.upload);        // Upload data
            traffic_option.series[1].data.push(-data.download);     // Inverted download data

            // Keep chart data points within 90 (3 minutes, every 2 seconds)
            if (traffic_option.xAxis.data.length > 90) {
                traffic_option.xAxis.data.shift();
                traffic_option.series[0].data.shift();
                traffic_option.series[1].data.shift();
            }

            // Update chart
            chart.setOption(traffic_option);

            // Update real-time traffic data display
            // document.getElementById('upload-speed').textContent = data.upload.toFixed(2);
            // document.getElementById('download-speed').textContent = data.download.toFixed(2);
        });
}

// Update data every 2 seconds
setInterval(updateData, 2000);