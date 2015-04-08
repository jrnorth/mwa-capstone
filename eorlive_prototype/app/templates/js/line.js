{
    title: {
        text: "{{data_source_str}}"
    },
    chart: {
        zoomType: "x"
    },
    credits: {
        enabled: false
    },
    xAxis: {
        type: 'datetime'
    },
    legend: {
        enabled: true
    },
    series: [
        {% for series in graph_data %}
        {
            name: "{{series}}",
            data: {{series}}
        },
        {% endfor %}
    ]
}
