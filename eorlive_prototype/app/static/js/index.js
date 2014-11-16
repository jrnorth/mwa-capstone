$(function() {
	var startDatePicker = $("#datepicker_start");
	var endDatePicker = $("#datepicker_end");
	startDatePicker.datetimepicker();
	endDatePicker.datetimepicker();

	var isStartDate = startDatePicker.val().length !== 0;
	var isEndDate = endDatePicker.val().length !== 0;

	if (!isStartDate || !isEndDate) {
		var now = new Date();
		var nowStr = getDateTimeString(now);

		var MS_PER_DAY = 86400000;
		var yesterday = new Date(now.getTime() - MS_PER_DAY);
		var yesterdayStr = getDateTimeString(yesterday);

		if (!isStartDate)
			startDatePicker.val(yesterdayStr);
		if (!isEndDate)
			endDatePicker.val(nowStr);
	}
});

function getDateTimeString(now) {
	var month = ("0" + (now.getMonth() + 1)).slice(-2);
	var date = ("0" + now.getDate()).slice(-2);
	var hours = ("0" + now.getHours()).slice(-2);
	var minutes = ("0" + now.getMinutes()).slice(-2);
	return (1900 + now.getYear()) + "/" + month + "/" + date + " " + hours + ":" + minutes;
};

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
