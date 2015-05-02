## Application Architecture

This section will explain, at a high level, how the application works.

### Backend
The Python code which controls the backend is located in the `.py` files in the `app` directory. Python is used to interact with the database and respond to clientside HTTP requests.

When a client makes an HTTP request to a "route" on the website (e.g. `eorlive-prototype.herokuapp.com/set/setname`), Flask calls the appropriate Python function designated with the matching `@app.route` (e.g. `@app.route(/set/<setName>)`). These app routes can be triggered by navigating to URLs, or by making explicit HTTP requests through AJAX (more on this below).

### Templates
The Python code for each route often responds by rendering a template. Templates are HTML files located in `app/templates`, and are modified on the backend during the render step before being served to the client. Jinja2 is the templating engine used to make these modifications. Jinja supports advanced syntax within the HTML, including for loops, if statements, etc. This makes it possible to dynamically generate pages. When the backend responds to an HTTP request, it typically obtains the needed data, then renders the template by passing those data as parameters. An example of Jinja code in an HTML page is below:

    <td class="cellClass profileCell">
        <h3>Your Profile</h3>
        Username: {{user.username}}
        <br>
        Name: {{user.first_name}} {{user.last_name}}
        <br>
        Email: {{user.email}}
    </td>

This HTML code generates a table cell dynamically, using attributes of the "user" parameter.

### Javascript
Javascript is used throughout the site to make the behavior dynamic (e.g. showing and hiding elements in response to user input), but is also used to interact with the database. By using JQuery and AJAX, Javascript code running on the clientside can make HTTP calls to various app routes, then "inject" the resulting HTML template into a component of the webpage. An example of such code is below:

    window.dataAmountRequest = $.ajax({
        type: "GET",
        url: "/data_amount",
        success: function(data) {
            $("#data_amount_table").html(data);
        },
        dataType: "html"
    });

Here, the AJAX requests defines the type of HTTP request, the url (identical to "app route"), and what should occur once the function succeeds. (AJAX is executed asynchronously, in the background). In this case, when it succeeds JQuery grabs the component of the page called 'data_amount_table' and puts the returned template into it.

Much of the Javascript code resides in `.js` files in the `app/static/js` directory. The `app/static` directory contains content for the website which does not change dynamically on the server. Other Javascript code can be found in `<script>` tags in the HTML files, when that code is specific to that HTML. Javascript which is in the `app/templates` directory is accessible to the Jinja library, and therefore can make use of the templating engine. This means that not only is HTML modified dynamically, but Javascript code is modified on the backend before being served to the client too.