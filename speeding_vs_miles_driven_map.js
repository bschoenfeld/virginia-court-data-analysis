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

var reds = d3.scale.linear().domain([0, 15])
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

var title = svg.append("text")
    .attr("x", 20)
    .attr("y", 20)
    .style("font-size", "16px")
    .style("z-index", "1000")
    .text("Frequency of Speeding Tickets");

function renderMap(speedingData) {
    gMap.append("g")
            .attr("id", "counties")
        .selectAll("path")
            .data(counties.features)
        .enter().append("path")
            .attr("d", path)
            .attr("style", function (d) {
                var fips = d.properties.COUNTYFP;
                if(fipsWithoutCourt.hasOwnProperty(fips)) {
                    fips = fipsWithoutCourt[fips];
                }
                fips = parseInt(fips);
                var value = speedingData[fips] || speedingData[fips + 1];
                var color = '#333';
                if(value) {
                    var colors = blues;
                    if(value < 0) {
                        colors = reds;
                        value = value * -1;
                    }

                    value = parseInt(value / 0.1);
                    color = colors(value);
                }
                return "fill: " + color;
            })
            .attr("data-fips", function (d) {
                return d.properties.COUNTYFP;
            });
    
    gMap.append("path")
        .datum(counties)
        .attr("id", "county-borders")
        .attr("d", path);
    
    var featureGroup = gMap.append('g').attr('class', 'feature-group');
    featureGroup.selectAll('.route')
        .data(roads.features)
        .enter()
            .append('path')
            .attr('class', 'route')
            .attr('d', path)
            .style('fill', 'white')
            .style('fill-opacity', 0)
            .style('stroke', '#333')
            .style('stroke-opacity', function(d) {
                if(d.properties.name && d.properties.name.indexOf('Interstate Route') !== -1)
                    return 0.9;
                return 0;
            })
            .style('stroke-width', 1.5);
}

// Load the data - Virginia counties in geojson
d3.json("data/counties_va.geojson", function(error, countyData) {
    if (error) {
        return console.error(error);
    }
    counties = countyData;

    d3.json("data/roadways_va.geojson", function(error, roadData) {
        if (error) {
            return console.error(error);
        }
        roads = roadData;

        d3.json("data/speeding_vs_miles_driven.json", function(error, speedingData) {
            if (error) {
                return console.error(error);
            }
            renderMap(speedingData);
        });
    });
});
