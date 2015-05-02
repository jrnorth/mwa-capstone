### Data Sources
On your profile page, you can create a custom data source in the bottom-left corner. A data source must specify a graph type, and you can choose a graph type in the dropdown menu. This page will explain how to add your own custom graph types to the site that all users will be able to use for their custom data sources.

### The Basics
Adding your own graph type will require you to write some code of your own (not exactly code per se, but that will be explained later). Each graph type will have exactly one corresponding JavaScript file in `eorlive_prototype/app/templates/js`. As of the writing of this page, two graph types have been included: column and line. The two files in this folder, `column.js` and `line.js`, correspond to these two graph types. Ultimately, this means that to add a new graph type you will have to add your new file, commit it to the repository, and redeploy the application to Heroku (these are just the basics are explained at a high level; they will be explained in more detail later).

### Walkthrough
In this section, we'll walk through `line.js` and explain what's going on.
```javascript
/* line.js */
{
    title: {
        text: "{{data_source_str}}"
    },
    chart: {
        zoomType: "x",
        events: {
            selection: function(event) {
                if (clickDragMode === 'flag') {
                    event.preventDefault();
                    flagClickAndDraggedRange(event);
                }
            }
        }
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
    {% if is_set %}
        {% for series in graph_data['series_dict'] %}
        {
            name: "{{series}}",
            data: {{series}}
        },
        {% endfor %}
    {% else %}
        {% for series in graph_data.h0 %}
        {
            name: "{{series}}",
            data: graph_data.{{series}}_h0
        },
        {% endfor %}
    {% endif %}
    ]
}
```
This is all the code required to allow users to create custom line charts using any data source!

Firstly, note that this file just contains a [JSON](http://json.org/example) object. This is because we're using [Highcharts](http://www.highcharts.com/) as our graphing library, and in Highcharts graphs are defined using the [options object](http://www.highcharts.com/docs/getting-started/how-to-set-options#1). The following code sample will help explain how custom graphs are created dynamically:
```javascript
$("#{{data_source_str_nospace}}").highcharts('StockChart',
    {% include template_name %}
, function (chart) {
    _chart = chart;
    setup();
});
```
Just pay attention to the line `{% include template_name %}`. Note that this is a [Jinja2 template](http://jinja.pocoo.org/docs/dev/) (the basics of Jinja2 templates are explained [here](https://github.com/dhganey/mwa-capstone/wiki/Application-Architecture)). So this line of code means that the code in the file whose name is `template_name` (which is a Python variable passed to the template and in this case has the value "line.js") will be passed to the `highcharts` function, which just takes the options object and creates the corresponding graph. Note that `line.js` is a Jinja2 template as well. To conclude: basically, you're providing a Highcharts configuration object that will be rendered by Jinja2 and passed into the `highcharts` function, which will create the graph that corresponds to the options you specify in the object.

**Important**: we are using Highstock, which is a specific module offered by Highcharts, and you can find the options documentation [here](http://api.highcharts.com/highstock) (we will also link to specific options where appropriate).

Now, back to `line.js`. The architecture we've provided for custom graph types will automatically pass some parameters to the template for you. One of these is `data_source_str` (as seen in [`title.text`](http://api.highcharts.com/highstock#title.text)), which is equal to the name of the data source using this graph type. For example, if we made a data source that displays quality statistics data as a line graph and we named it "QS", then data_source_str would equal "QS". The `text` of your custom graph's `title` **must** be `"{{data_source_str}}"`, which, again, injects the value of `data_source_str` into the template as the graph title. You can just copy-paste the `title` object into your code as-is. If you want to style your graph's title, feel free to customize more of the options listed in the [`title`](http://api.highcharts.com/highstock#title) documentation.

Now let's look at the `chart` object. [`zoomType`](http://api.highcharts.com/highstock#chart.zoomType) is "x", which means that you can click-and-drag on the graph to zoom in to a region. [`events.selection`](http://api.highcharts.com/highstock#chart.events.selection) is a JavaScript function that is called on click-and-drag events. `clickDragMode` is a JavaScript variable that you don't have to worry about; it just remembers whether the user has selected _zooming_ mode or _flagging_ mode on the graph. This function stops the default behavior of the `selection` event (which is zooming) and instead flags that data region on the graph. This function **must** be present or data flagging will not work on your graph. Unless you have a need to add more custom options in the `chart` object (which is unlikely), you can just copy-paste it into your code as-is.

Next, let's look at the [`credits`](http://api.highcharts.com/highstock#credits) object. We set the `enabled` property to `false`, which prevents a Highcharts hyperlink from appearing in the bottom-right corner of the graph. We strongly recommend copying-pasting the `credits` object into your custom graph as-is, because we have our own graph controls in the bottom-right corner and it's easy to accidentally click on the hyperlink instead.

The [`xAxis`](http://api.highcharts.com/highstock#xAxis) object is extremely important. Specifically, `xAxis.type` is set to 'datetime', which is critical to the functionality of the graph. This setting means that the x-axis of the graph is expressed in datetimes, so data will always be viewed in order of time. **All** graphs on the site use datetimes on the x-axis, since all their data are indexed by observation IDs (which are GPS time values). The data requested by a data source will be passed to the graph (as will be explained shortly) with datetime values on the x-axis, so you **must** specify 'datetime' for `xAxis.type` or the graph **will not** work at all. Again, you can copy-paste the `xAxis` object into your code.

In the [`legend`](http://api.highcharts.com/highstock#legend) object, we set one property, `enabled`, to `true`. The legend in the graph shows you the color that corresponds to each data series, and you can click on the legend entries to enable or disable their corresponding series in the graph. We strongly recommend enabling the legend in your code. You can just copy-paste the `legend` object as-is.

Finally, we have the [`series`](http://api.highcharts.com/highstock#series) array, which contains the data to be displayed by the chart. Notice that we have a Jinja2 `if` statement here. `is_set` is `true` if the user is viewing a specific Set, and `false` otherwise (the user is just viewing a date range). In your custom graph type, you will need to provide support for both of these cases.

#### First case: A Set
In this case, we have a Jinja2 `for` loop that iterates over the keys in the dictionary `graph_data['series_dict']`. Each key is the name of a column specified in the data source the graph is displaying. For example, if we're using the `qs` table in the `mwa_qc` database and requested `window_x` and `window_y` as the columns in our data sources, the keys in this dictionary would be "window_x" and "window_y". So, for every data series specified by the user's data source, we include an entry in the `series` array. `name` is just the series title that's displayed in the graph; we place quotes around it so it will be rendered as a string literal in JavaScript. `data` is the array containing the actual series data. `{{series}}` just places the value of the `series` Python variable (a string, the name of the data series) as text in the JavaScript file _without quotes_. In other words, it just takes the text inside the `series` variable and places it in the file. The result, when the template is rendered, is that a JavaScript variable with the same name as the data series is being assigned to the `data` property. Going back to our `qs` example, the rendered result would be:
```javascript
{
    name: "window_x",
    data: window_x
},
{
    name: "window_y",
    data: window_y
},
```
Note: there is no guarantee that the data source's columns will be returned in any specific order.

Behind the scenes, our architecture has already created a JavaScript variable for each column in the data source that contains the series data (actually, you can see this in `graph.html` in the `templates` folder). So all you're doing is referencing the variable that already contains the data you want!

#### Case 2: A Date Range
In this case, we have a Jinja2 `for` loop that iterates over all the keys in the dictionary `graph_data.h0`. As in the previous case, each key is the name of a column specified in the data source the graph is displaying. But you may be wondering what the `h0` means. If you've read the wiki section about [how to use the site](https://github.com/dhganey/mwa-capstone/wiki/Website-Usage), then you know about high/low and EOR0/EOR1 and how they apply to data sets. Here, the `h0` means that the graph will show the data set containing the observations that correspond to 'high' and 'EOR0'. The high/low and EOR0/EOR1 controls on the graph are set to 'high' and 'EOR0' by default, and that is why we apply the `h0` data at the start. So, the `graph_data` also contains dictionaries named `h1`, `l0`, `l1`, each of which contains the correct data for all of the series in the user's data source. We have already implemented the logic that handles switching between high/low and EOR0/EOR1 data sets when the user makes a selection in the dropdown, so you don't have to worry about it. When the user views a date range, he can view the data for all the different high/low and EOR0/EOR1 subsets. This is in contrast to a set, which already has high/low and EOR0/EOR1 associated with it (i.e., this is why we have two different cases).

The `name` property works in just the same way as in the previous case, but the `data` property is implemented a bit differently. When the user is viewing a date range, instead of providing a separate JavaScript variable for each column in the data source, we provide one dictionary called graph_data that contains the data for each column at each high/low and EOR0/EOR1 combination. Each key in the dictionary is of the form "series_name_h0", and there is an entry for each series at each of 'h0', 'h1', 'l0', and 'l1'. The statement `graph_data.{{series}}_h0` works in the way that was described for the previous case: `{{series}}` will just insert the value of the `series` Python variable without quotation marks, so we end up with a JavaScript variable reference.

Therefore, our `qs` example will generate code that looks like this:
```javascript
{
    name: "window_x",
    data: graph_data.window_x_h0
},
{
    name: "window_x",
    data: graph_data.window_x_h1
},
{
    name: "window_x",
    data: graph_data.window_x_l0
},
{
    name: "window_x",
    data: graph_data.window_x_l1
},
// There will be four more entries with window_y instead of window_x
```

#### Summary
For your graph type to work correctly with both sets and date ranges, you **must** support both cases! For graph types that treat each series equally (i.e., you just want to display some number of series in an area chart), you can just copy-paste the `series` array as-is.

### A Few Modifications
Now let's take a quick look at `column.js`, which will demonstrate how to make minor modifications for different graph types.
```javascript
/* column.js */
{
    title: {
        text: "{{data_source_str}}"
    },
    chart: {
        type: "column",
        zoomType: "x",
        events: {
            selection: function(event) {
                if (clickDragMode === 'flag') {
                    event.preventDefault();
                    flagClickAndDraggedRange(event);
                }
            }
        }
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
    plotOptions: {
        column: {
            dataGrouping: {
                approximation: "average",
                groupPixelWidth: 80,
                forced: true
            },
            pointPlacement: "between",
            groupPadding: 0.1,
            pointPadding: 0
        }
    },
    series: [
    {% if is_set %}
        {% for series in graph_data['series_dict'] %}
        {
            name: "{{series}}",
            data: {{series}}
        },
        {% endfor %}
    {% else %}
        {% for series in graph_data.h0 %}
        {
            name: "{{series}}",
            data: graph_data.{{series}}_h0
        },
        {% endfor %}
    {% endif %}
    ]
}
```
The first thing to note is that we've specified a `type` property for the `chart` object. In Highcharts, 'line' is the default chart type, but you can specify different graph types, like 'column'.

Also, note that we've added a new object as a property of the Highcharts configuration object: the [`plotOptions`](http://api.highcharts.com/highstock#plotOptions) object. In this object, we specify a number of special options available for column graphs. We won't go into detail about them here since Highcharts has excellent documentation; we just want you to see that it's extremely easy to add custom options to your graph without complicated code modifications. Note that the differences listed here are the only differences between this file and `line.js`. Our recommendation for creating new graph types is to copy-paste the code in `line.js` and make your customizations from there.

### Developing, Testing, and Deploying Your New Graph Type
The first step in creating your custom graph type is to come up with a name for it. The name must be unique, but it also cannot differ from another graph type's name in case only. For example, you should not create a custom graph type named 'line' because there is already one named 'Line'. This is because of the naming convention we use for the files associated with graph types. When you create a graph type, the name of the corresponding `.js` file you create must be a lowercase version of the name you gave to the graph type. For example, if want a graph type named 'My_Cool_Graph', the `.js` file you create **must** be named 'my_cool_graph.js'. Once you've decided on a name, you need to insert it into the `graph_type` table in the database on your local machine (it's the only column in the table). Then, create your `.js` file in the `templates/js` folder.

The second step is to write your code in the `.js` file you created. After you're done with that, you should run the site locally and create a data source using the new graph type (it should show up in the dropdown menu).

The third step is to test it out. Activate the test data source you created locally and view it on the main page. Try using it to view both sets and date ranges. Try constructing sets by flagging data on it. Does it display the data correctly and in the way you expected it to? If so, we recommend creating at least one more data source to test it with.

Once you're satisfied with your new graph type, commit the new file to the repository and redeploy the site to Heroku. After you've done that, you'll have to go into the live site's database and manually insert the name of the new graph type as you did above on your local machine (for this, we recommend running [`heroku pg:psql`](https://devcenter.heroku.com/articles/heroku-postgresql), which requires you to have psql installed locally). Once that's done, all users of the site will be able to use your new graph type in their data sources!