$(function() {
	$("#datepicker_start").datetimepicker();
	$("#datepicker_end").datetimepicker();
});

function getObservations() {
	var start = $("#datepicker_start").val();
	var end = $("#datepicker_end").val();
	re = /^\d{4}\/\d{2}\/\d{2} \d{2}:\d{2}$/;

	var LEAP_SECONDS = 16;

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

	var gpsTimeBegin = new Date(1980, 0, 6, 0, 0, 0);
	var starttime = startDate.getTime();
	var endtime = endDate.getTime();
	starttime = Math.floor((starttime - gpsTimeBegin) / 1000) + LEAP_SECONDS;
	endtime = Math.floor((endtime - gpsTimeBegin)/1000) + LEAP_SECONDS;

	$.ajax({
		type: "POST",
		url: "/get_observations",
		data: {'starttime': starttime, 'endtime': endtime},
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
