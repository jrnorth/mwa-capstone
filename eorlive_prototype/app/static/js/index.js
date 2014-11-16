$(function() {
	var startDatePicker = $("#datepicker_start");
	var endDatePicker = $("#datepicker_end");
	startDatePicker.datetimepicker();
	endDatePicker.datetimepicker();

	var now = new Date();
	var nowStr = (1900 + now.getYear()) + "/" + (now.getMonth() + 1) + "/" + now.getDate() + " " + now.getHours() + ":" + now.getMinutes();

	if (startDatePicker.val().length === 0)
		startDatePicker.val(nowStr);
	if (endDatePicker.val().length === 0)
		endDatePicker.val(nowStr);
});

function getObservations() {
	var start = $("#datepicker_start").val();
	var end = $("#datepicker_end").val();
	re = /^\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}$/;

	var startDate, endDate;

	if (start.match(re)) {
		startDate = getDate(start);
	} else {
		alert("Invalid datetime format: " + start);
		return;
	}

	if (end.match(re)) {
		endDate = getDate(end);
	} else {
		alert("Invalid datetime format: " + end);
		return;
	}

	$("#observations_div").html("<img src='/static/images/ajax-loader.gif' class='loading'/>");

	var startUTC = startDate.toISOString();
	var endUTC = endDate.toISOString();

	$.ajax({
		type: "POST",
		url: "/get_observations",
		data: {'starttime': startUTC, 'endtime': endUTC},
		success: function(data) {
			$("#observations_div").html(data);
		},
		dataType: "html"
	});
};

function getDate(datestr) {
	var year = datestr.substring(0, 4);
	var month = datestr.substring(5, 7);
	var day = datestr.substring(8, 10);
	var hour = datestr.substring(11, 13);
	var minute = datestr.substring(14, 16);
	return new Date(year, month - 1, day, hour, minute, 0);
};
