function renderSets(filterType, startUTC, endUTC) {
    $("#set_list_div").html("<img src='/static/images/ajax-loader.gif' class='loading'/>");

    window.setRequest = $.ajax({
        type: "POST",
        url: "/get_sets",
        data: {'filter_type': filterType, 'starttime': startUTC, 'endtime': endUTC},
        success: function(data) {
            $("#set_list_div").html(data);
        },
        dataType: 'html'
    });
};

function deleteSet(setName) {
    $.ajax({
        type: "POST",
        url: "/delete_set",
        data: {'set_name': setName},
        success: function(data) {
            document.write(data);
        },
        dataType: 'html'
    });
};
