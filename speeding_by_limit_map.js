/* 
 * Mapping of FIPS counties on the map with no court
 * to the FIPS of the court they use 
 * e.g. Harrisonburg is an independent city but uses
 * the Rockingham County court system
 */
var fipsWithoutCourt = {
    '735': '199',
    '095': '830',
    '683': '153',
    '685': '153',
    '720': '195',
    '678': '163',
    '660': '165',
    '580': '005'
};

var lightRed = '#FF998B';
var darkRed = '#BE1700';
var lightBlue = '#8BF1FF';
var darkBlue = '#00A7BE';

var reds = d3.scale.linear().domain([0, 30])
             .interpolate(d3.interpolateHcl)
             .range([d3.rgb(lightRed), d3.rgb(darkRed)]);
// light blue => dark blue
var blues = d3.scale.linear().domain([0, 15])
               .interpolate(d3.interpolateHcl)
               .range([d3.rgb(lightBlue), d3.rgb(darkBlue)]);

var canvas = document.getElementById('map-key');
var ctx = canvas.getContext('2d');

var gradient = ctx.createLinearGradient(50, 0, 890, 0);
gradient.addColorStop(0, darkRed);
gradient.addColorStop(0.5, lightRed);
gradient.addColorStop(0.5, lightBlue);
gradient.addColorStop(1, darkBlue);
ctx.fillStyle = gradient;
ctx.fillRect(50, 0, 890, 10);

/*
 * Create the map SVG
 * Scale and translate the project for Virginia.
 * The translation is some super hacky trial and 
 * error shit because I have no idea what I'm doing.
 */
var width = 960,
    height = 600,
    scale = 6000,
    centered,
    counties,
    roads;

var projection = d3.geo.mercator()
    .scale(scale)
    .translate([width * (scale / width + 2.9), height * (scale / height - 2.4)]);

var path = d3.geo.path()
    .projection(projection);

var svg = d3.select("#map").append("svg")
    .attr("width", width)
    .attr("height", height);

svg.append("rect")
    .attr("class", "background")
    .attr("width", width)
    .attr("height", height);

var gMap = svg.append("g");

function getSpeedingDataRow(speedingData, fips) {
    var fips = fips.substring(2);
    if(fipsWithoutCourt.hasOwnProperty(fips)) {
        fips = fipsWithoutCourt[fips];
    }
    fips = parseInt(fips);
    for(var row in speedingData) {
        if(speedingData[row]['fips'] == fips) {
            return speedingData[row];
        }
    }
    return null;
}

function renderMap(speedingData) {
    gMap.append("g")
            .attr("id", "counties")
        .selectAll("path")
            .data(counties.features)
        .enter().append("path")
            .attr("d", path)
            .attr("style", function (d) {
                var row = getSpeedingDataRow(speedingData, d.properties.STCOFIPS);
                var value = row ? row['Average'] : 0;
                var color = '#ccc';
                if(value) {
                    var colors = reds;
                    if(value < 0) {
                        colors = reds;
                        value = value * -1;
                    }

                    value = parseFloat(value) * 10;
                    color = colors(value);
                }
                return "fill: " + color;
            })
            .attr("data-fips", function (d) {
                return d.properties.STCOFIPS.substring(2);
            });

    gMap.append("path")
        .datum(counties)
        .attr("id", "county-borders")
        .attr("d", path);
    
    var featureGroup = gMap.append('g').attr('class', 'feature-group');
    featureGroup.selectAll('.route')
        .data(roads.geometries)
        .enter()
            .append('path')
            .attr('class', 'route')
            .attr('d', path)
            .style('fill', 'white')
            .style('fill-opacity', 0)
            .style('stroke', '#777')
            .style('stroke-opacity', 0.7)
            .style('stroke-width', 1.5);
    
    gMap.selectAll("text")
        .data(counties.features)
        .enter()
        .append("rect");

    gMap.selectAll("text")
        .data(counties.features)
        .enter()
        .append("text")
        .text(function(d){
            var row = getSpeedingDataRow(speedingData, d.properties.STCOFIPS);
            if (d.properties.NAME == "Covington")
                return null;
            if(row) {
                console.log(row);
                return d.properties.NAME;
            }
            return null;
        })
        .attr("x", function(d){
            var buffer = 0;

            // 35
            //if (d.properties.NAME == "Buena Vista") buffer += 10;
            //if (d.properties.NAME == "Chesapeake") buffer += 10;

            // 45
            //if (d.properties.NAME == "Emporia") buffer += 35;

            // 55
            //if (d.properties.NAME == "Greensville") buffer += 10;

            // 65
            //if (d.properties.NAME == "Emporia") buffer -= 10;
            //if (d.properties.NAME == "Southampton") buffer += 20;

            // 70
            if (d.properties.NAME == "Bristol") buffer -= 25;

            return path.centroid(d)[0] + buffer;
        })
        .attr("y", function(d){
            var buffer = 0;

            // 35
            //buffer -= 10;

            // 45
            //if (d.properties.NAME == "Danville") buffer -= 10;
            //if (d.properties.NAME == "Buena Vista") buffer -= 10;
            //if (d.properties.NAME == "Greensville") buffer -= 25;

            // 55
            //if (d.properties.NAME == "Buckingham") buffer -= 5;
            //if (d.properties.NAME == "Charles City") buffer -= 10;
            //if (d.properties.NAME == "Cumberland") buffer += 10;
            //if (d.properties.NAME == "Greensville") buffer += 10;

            // 65
            //if (d.properties.NAME == "Southampton") buffer += 10;
            //if (d.properties.NAME == "Emporia") buffer -= 10;

            //70
            buffer -= 10;
            if (d.properties.NAME == "Bristol") buffer += 7;

            return path.centroid(d)[1] + buffer;
        })
        .attr("font-family", "Helvetica")
        .attr("text-anchor", "middle")
        .attr("fill", "white")
        .attr("font-size", "14px");
    
    gMap.selectAll("text").each(function(d) {
        d.bb = this.getBBox();
    });

    var paddingLeftRight = 6; // adjust the padding values depending on font and font size
    var paddingTopBottom = 4;

    gMap.selectAll("rect")
        .attr("fill", "black")
        .style("fill-opacity", 0.7)
        .attr("rx", 3)
        .attr("ry", 3)
        .attr("x", function(d) { return d.bb.x - paddingLeftRight/2; })
        .attr("y", function(d) { return d.bb.y - paddingTopBottom/2; })
        .attr("width", function(d) { return d.bb.width + paddingLeftRight; })
        .attr("height", function(d) { return d.bb.height + paddingTopBottom; });
}

// Load the data - Virginia counties in geojson
d3.json("data/VA_COUNTY.json", function(error, countyData) {
    if (error) {
        return console.error(error);
    }
    counties = countyData;

    d3.json("data/interstates_va.json", function(error, roadData) {
        if (error) {
            return console.error(error);
        }
        roads = roadData;

        d3.csv("data/speeding_limit_70_weighted_5_9.csv", function(error, speedingData) {
            if (error) {
                return console.error(error);
            }
            renderMap(speedingData);
        });
    });
});
