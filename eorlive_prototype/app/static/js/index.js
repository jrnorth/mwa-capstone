$(function() {
	$("#datepicker_start").datetimepicker();
	$("#datepicker_end").datetimepicker();
	$("#observations_div").hide();	
	$("#no_obs_label").hide();
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

	var div = $("#observations_div");
	var table = div.find("table");
	var tbody = table.find("tbody").empty();
	div.hide();

	$.ajax({
		type: "POST",
		url: "/get_observations",
		data: {'starttime': starttime, 'endtime': endtime},
		success: function(data) {
			if (data !== undefined && data.observations.length > 0) {
				$("#no_obs_label").hide();
				$.each(data.observations, function(i, v) {
					tbody.append("<tr>")
						.append("<td>" + v[0] + "</td>")
						.append("<td>" + v[1] + "</td>")
						.append("<td>" + v[2] + "</td>")
						.append("</tr>");
				});
				table.show();
			} else {
				$("#no_obs_label").show();
				table.hide();
			}
			div.show();
		},
		dataType: "json"
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
