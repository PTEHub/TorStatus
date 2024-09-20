// Global variables
var backgroundNodes = [];
var circuitData = {};
var colorScheme = {
    'Local': '#ff00ff',
    'Entry': '#3ed4ff',
    'Middle': '#ffa022',
    'Exit': '#a6c84c',
    'Target': '#E0515C'
};
var geoCoordMap = {};
var typeData = {
    'Local': [],
    'Entry': [],
    'Middle': [],
    'Exit': [],
    'Target': []
};
var circuitTypeData = {
    'Local': [],
    'Entry': [],
    'Middle': [],
    'Exit': [],
    'Target': []
};
var lines = [];
var option = {};
var myecharts;
var maxCircuits = 10;
var circuitClearInterval;

// Initialization function
function initTorNetworkVisualization(initialBackgroundNodes, initialCircuitData) {
    backgroundNodes = initialBackgroundNodes || [];
    circuitData = initialCircuitData || {};

    // Initialize ECharts instance
    myecharts = echarts.init(document.querySelector('.map .geo'));

    // Initialize options
    initializeOption();

    // Process data and update chart
    processData();
    myecharts.setOption(option);

    // Add functionality to clear circuits periodically
    startCircuitClearInterval();
}

// Initialize options
function initializeOption() {
    option = {
        backgroundColor: '#080a20',
        title: {
            text: 'Tor Network Nodes and Circuit Path',
            left: 'center',
            top: '5%',
            textStyle: {
                color: '#fff'
            }
        },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                if (params.data && params.data.ip) {
                    var info = (params.data.name || params.data.ip) + '<br/>IP: ' + params.data.ip +
                               '<br/>Country: ' + params.data.country +
                               '<br/>Type: ' + params.data.type;
                    if (params.data.bandwidth > 0) {
                        info += '<br/>Bandwidth: ' + params.data.bandwidth + ' kb/s';
                    }
                    if (params.data.isCircuitNode) {
                        info += '<br/>(Circuit Node)';
                    }
                    return info;
                }
                return params.name;
            }
        },
        legend: {
            orient: 'vertical',
            top: 'bottom',
            left: 'right',
            data: [
                {name: 'Local', icon: 'circle'},
                {name: 'Entry', icon: 'circle'},
                {name: 'Middle', icon: 'circle'},
                {name: 'Exit', icon: 'circle'},
                {name: 'Target', icon: 'circle'},
                {name: 'Circuit Path', icon: 'line'}
            ],
            textStyle: {
                color: '#fff'
            },
            selectedMode: 'multiple',
            itemWidth: 15,
            itemHeight: 15,
            itemGap: 10
        },
        geo: {
            map: 'world',
            roam: true,
            zoom: 1.1,
            label: {
                emphasis: {
                    show: false
                }
            },
            itemStyle: {
                normal: {
                    areaColor: '#142957',
                    borderColor: '#0692a4'
                },
                emphasis: {
                    areaColor: '#0b1c2d'
                }
            }
        },
        series: [
            {
                name: 'Background Nodes',
                type: 'effectScatter',
                coordinateSystem: 'geo',
                data: [],
                symbolSize: function (val) {
                    return Math.max((val[2] || 0) / 5000, 10);
                },
                showEffectOn: 'render',
                rippleEffect: {
                    brushType: 'stroke',
                    color: null  // Use the same color as the node
                },
                hoverAnimation: true,
                label: {
                    normal: {
                        show: false
                    }
                },
                itemStyle: {
                    normal: {
                        color: function(params) {
                            return colorScheme[params.data.type] || '#ffffff';
                        },
                        shadowBlur: 10,
                        shadowColor: function(params) {
                            return (colorScheme[params.data.type] || '#ffffff') + '80';
                        }
                    }
                },
                zlevel: 1
            },
            {
                name: 'Circuit Path',
                type: 'lines',
                coordinateSystem: 'geo',
                zlevel: 2,
                effect: {
                    show: true,
                    period: 6,
                    trailLength: 0.7,
                    color: '#fff',
                    symbolSize: 3
                },
                lineStyle: {
                    normal: {
                        color: '#a6c84c',
                        width: 0,
                        curveness: 0.2
                    }
                },
                data: []
            }
        ]
    };

    // Add a separate series for each type of node
    Object.keys(colorScheme).forEach(function(type) {
        option.series.push({
            name: type,
            type: 'effectScatter',
            coordinateSystem: 'geo',
            data: [],
            symbolSize: function (val) {
                return Math.max((val[2] || 0) / 5000, 10);
            },
            showEffectOn: 'render',
            rippleEffect: {
                brushType: 'stroke',
                color: null  // Use the same color as the node
            },
            hoverAnimation: true,
            itemStyle: {
                normal: {
                    color: colorScheme[type],
                    shadowBlur: 10,
                    shadowColor: colorScheme[type] + '80'
                }
            },
            zlevel: 3
        });
    });
}

// Update background nodes data
function updateBackgroundNodes(newBackgroundNodes) {
    if (!Array.isArray(newBackgroundNodes)) {
        console.error('Invalid backgroundNodes data');
        clearBackgroundNodes();
        updateChart();
        return;
    }

    backgroundNodes = newBackgroundNodes;
    processBackgroundNodes();
}

// Update circuit data
function updateCircuitData(newCircuitData) {
    if (typeof newCircuitData !== 'object' || newCircuitData === null) {
        console.error('Invalid circuitData');
        return;
    }

    processNewCircuitData(newCircuitData);
    // updateChart() is called inside processNewCircuitData
}

// Process new circuit data
function processNewCircuitData(newCircuitData) {
    if (!newCircuitData || typeof newCircuitData !== 'object') {
        console.error('Invalid newCircuitData');
        return;
    }

    // If the number of circuits reaches the maximum, remove the oldest one
    if (lines.length >= maxCircuits) {
        lines.shift();
        // Also need to remove corresponding node data, simplified here by clearing previous data
        circuitTypeData = {
            'Local': [],
            'Entry': [],
            'Middle': [],
            'Exit': [],
            'Target': []
        };
    }

    // Process local public IP
    if (newCircuitData.local_public_ip && Array.isArray(newCircuitData.local_public_ip) && newCircuitData.local_public_ip.length > 0) {
        var localIP = newCircuitData.local_public_ip[0];
        if (localIP && localIP.ip && localIP.longitude && localIP.latitude) {
            geoCoordMap[localIP.ip] = [localIP.longitude, localIP.latitude];
            if (!circuitTypeData['Local'].some(node => node.ip === localIP.ip)) {
                circuitTypeData['Local'].push({
                    name: 'Local',
                    value: [localIP.longitude, localIP.latitude, 0],
                    ip: localIP.ip,
                    bandwidth: 0,
                    country: localIP.country || 'Unknown',
                    type: 'Local',
                    isCircuitNode: true
                });
            }
        }
    }

    // Process circuit path data
    if (Array.isArray(newCircuitData.path)) {
        var fullPath = (newCircuitData.local_public_ip && newCircuitData.local_public_ip[0]) ?
            [newCircuitData.local_public_ip[0]].concat(newCircuitData.path) :
            newCircuitData.path;

        fullPath.forEach(function(item, index) {
            if (index > 0 && item && item.ip && item.longitude && item.latitude && item.type) {
                geoCoordMap[item.ip] = [item.longitude, item.latitude];
                if (!circuitTypeData[item.type].some(node => node.ip === item.ip)) {
                    circuitTypeData[item.type].push({
                        name: item.nickname || item.ip,
                        value: [item.longitude, item.latitude, item.bandwidth || 0],
                        ip: item.ip,
                        bandwidth: item.bandwidth || 0,
                        country: item.country || 'Unknown',
                        type: item.type,
                        isCircuitNode: true
                    });
                }
            }

            if (index < fullPath.length - 1) {
                var nextItem = fullPath[index + 1];
                if (item && nextItem && item.longitude && item.latitude && nextItem.longitude && nextItem.latitude) {
                    lines.push({
                        coords: [[item.longitude, item.latitude], [nextItem.longitude, nextItem.latitude]]
                    });
                }
            }
        });
    }

    // Add target data
    if (newCircuitData.target_geolocation && newCircuitData.stream_target) {
        var targetCoord = [newCircuitData.target_geolocation.longitude, newCircuitData.target_geolocation.latitude];
        geoCoordMap[newCircuitData.stream_target] = targetCoord;

        // Check if this target already exists
        if (!circuitTypeData['Target'].some(target => target.ip === newCircuitData.stream_target)) {
            circuitTypeData['Target'].push({
                name: 'Target',
                value: targetCoord.concat(0),
                ip: newCircuitData.stream_target,
                country: newCircuitData.target_geolocation.country || 'Unknown',
                type: 'Target'
            });
        }

        // Add a line from the last node to the target
        var lastNode = fullPath[fullPath.length - 1];
        if (lastNode && lastNode.longitude && lastNode.latitude) {
            lines.push({
                coords: [[lastNode.longitude, lastNode.latitude], targetCoord]
            });
        }
    }

    // Ensure the total number of circuits doesn't exceed maxCircuits after processing new circuits
    if (lines.length > maxCircuits) {
        lines = lines.slice(-maxCircuits);
    }

    updateChart();
}

// Process data
function processData() {
    resetDataStructures();
    processBackgroundNodes();
    processCircuitData();
}

// Reset data structures
function resetDataStructures() {
    geoCoordMap = {};
    typeData = {
        'Local': [],
        'Entry': [],
        'Middle': [],
        'Exit': [],
        'Target': []
    };
    circuitTypeData = {
        'Local': [],
        'Entry': [],
        'Middle': [],
        'Exit': [],
        'Target': []
    };
    lines = [];
}

// Process background nodes data
function processBackgroundNodes() {
    if (!Array.isArray(backgroundNodes)) {
        console.error('backgroundNodes is not an array');
        clearBackgroundNodes();
        return;
    }

    clearBackgroundNodes(); // Clear existing data

    backgroundNodes.forEach(function(item) {
        if (item && item.ip && item.longitude && item.latitude && item.type && item.type !== 'Local') {
            geoCoordMap[item.ip] = [item.longitude, item.latitude];
            typeData[item.type] = typeData[item.type] || [];
            typeData[item.type].push({
                name: item.ip,
                value: [item.longitude, item.latitude, item.bandwidth || 0],
                ip: item.ip,
                bandwidth: item.bandwidth || 0,
                country: item.country || 'Unknown',
                type: item.type
            });
        }
    });

    updateChart(); // Ensure chart updates to reflect changes
}

// New helper function: Clear background nodes data
function clearBackgroundNodes() {
    geoCoordMap = {};
    typeData = {
        'Local': [],
        'Entry': [],
        'Middle': [],
        'Exit': [],
        'Target': []
    };
    // Note: We don't clear circuitTypeData here as it contains circuit information
}

// Process circuit data
function processCircuitData() {
    if (!circuitData || typeof circuitData !== 'object') {
        console.error('Invalid circuitData');
        return;
    }

    // Process local public IP
    if (circuitData.local_public_ip && Array.isArray(circuitData.local_public_ip) && circuitData.local_public_ip.length > 0) {
        var localIP = circuitData.local_public_ip[0];
        if (localIP && localIP.ip && localIP.longitude && localIP.latitude) {
            geoCoordMap[localIP.ip] = [localIP.longitude, localIP.latitude];
            circuitTypeData['Local'] = [{
                name: 'Local',
                value: [localIP.longitude, localIP.latitude, 0],
                ip: localIP.ip,
                bandwidth: 0,
                country: localIP.country || 'Unknown',
                type: 'Local',
                isCircuitNode: true
            }];
        }
    } else {
        console.warn('No valid local_public_ip data found');
    }

    // Process circuit path data
    if (Array.isArray(circuitData.path)) {
        var fullPath = (circuitData.local_public_ip && circuitData.local_public_ip[0]) ?
            [circuitData.local_public_ip[0]].concat(circuitData.path) :
            circuitData.path;

        fullPath.forEach(function(item, index) {
            if (index > 0 && item && item.ip && item.longitude && item.latitude && item.type) {
                geoCoordMap[item.ip] = [item.longitude, item.latitude];
                circuitTypeData[item.type] = circuitTypeData[item.type] || [];
                circuitTypeData[item.type].push({
                    name: item.nickname || item.ip,
                    value: [item.longitude, item.latitude, item.bandwidth || 0],
                    ip: item.ip,
                    bandwidth: item.bandwidth || 0,
                    country: item.country || 'Unknown',
                    type: item.type,
                    isCircuitNode: true
                });
            }

            if (index < fullPath.length - 1) {
                var nextItem = fullPath[index + 1];
                if (item && nextItem && item.longitude && item.latitude && nextItem.longitude && nextItem.latitude) {
                    lines.push({
                        coords: [[item.longitude, item.latitude], [nextItem.longitude, nextItem.latitude]]
                    });
                }
            }
        });
    }

    // Add target data
    if (circuitData.target_geolocation && circuitData.stream_target) {
        var targetCoord = [circuitData.target_geolocation.longitude, circuitData.target_geolocation.latitude];
        geoCoordMap[circuitData.stream_target] = targetCoord;

        // Check if this target already exists
        var existingTarget = circuitTypeData['Target'].find(target => target.ip === circuitData.stream_target);
        if (!existingTarget) {
            circuitTypeData['Target'].push({
                name: 'Target',
                value: targetCoord.concat(0),
                ip: circuitData.stream_target,
                country: circuitData.target_geolocation.country || 'Unknown',
                type: 'Target'
            });
        }

        // Add a line from the last node to the target
        var lastNode = fullPath[fullPath.length - 1];
        if (lastNode && lastNode.longitude && lastNode.latitude) {
            lines.push({
                coords: [[lastNode.longitude, lastNode.latitude], targetCoord]
            });
        }
    }
}

// Update chart
function updateChart() {
    // Update background nodes data
    option.series[0].data = [].concat(
        typeData.Entry || [],
        typeData.Middle || [],
        typeData.Exit || []
    );

    // Update circuit path
    option.series[1].data = lines;

    // Update data for each type of node
    Object.keys(colorScheme).forEach(function(type, index) {
        option.series[index + 2].data = circuitTypeData[type] || [];
    });

    // Reset options
    if (myecharts && typeof myecharts.setOption === 'function') {
        myecharts.setOption(option);
    } else {
        console.error('ECharts instance is not properly initialized');
    }
}

// Start periodic circuit clearing
function startCircuitClearInterval() {
    if (circuitClearInterval) {
        clearInterval(circuitClearInterval);
    }
    circuitClearInterval = setInterval(function() {
        clearAllCircuits(); // Use the modified clearAllCircuits function
    }, 30000); // 30 seconds
}

// Clear all circuits
function clearAllCircuits() {
    lines = [];
    var localNode = circuitTypeData['Local'][0]; // Save local node data
    circuitTypeData = {
        'Local': localNode ? [localNode] : [], // Retain local node if it exists
        'Entry': [],
        'Middle': [],
        'Exit': [],
        'Target': []
    };
    updateChart();
}

// Expose public functions
window.TorNetworkVisualization = {
    init: initTorNetworkVisualization,
    updateBackgroundNodes: updateBackgroundNodes,
    updateCircuitData: updateCircuitData,
    clearAllCircuits: clearAllCircuits,
    clearBackgroundNodes: clearBackgroundNodes // Add new public method
};