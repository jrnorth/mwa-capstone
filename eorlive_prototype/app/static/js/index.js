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

	$("#data_amount_table").html("<img src='/static/images/ajax-loader.gif' class='loading'/>");

	$.ajax({
		type: "GET",
		url: "/data_amount",
		success: function(data) {
			$("#data_amount_table").html(data);
		},
		dataType: "html"
	});

	getObservations();
});

function getDateTimeString(now) {
	var month = ("0" + (now.getUTCMonth() + 1)).slice(-2);
	var date = ("0" + now.getUTCDate()).slice(-2);
	var hours = ("0" + now.getUTCHours()).slice(-2);
	var minutes = ("0" + now.getUTCMinutes()).slice(-2);
	return now.getUTCFullYear() + "/" + month + "/" + date + " " + hours + ":" + minutes;
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

	$("#observations_summary").html("<img src='/static/images/ajax-loader.gif' class='loading'/>");
	$("#comments_div").html("<img src='/static/images/ajax-loader.gif' class='loading'/>");

	// Make each date into a string of the format "YYYY-mm-ddTHH:MM:SSZ", which is the format used in the local database.
	var startUTC = startDate.toISOString().slice(0, 19) + "Z";
	var endUTC = endDate.toISOString().slice(0, 19) + "Z";

	$.ajax({
		type: "POST",
		url: "/histogram_data",
		data: {'starttime': startUTC, 'endtime': endUTC},
		success: function(data) {
			$("#observations_summary").html(data);
		},
		dataType: "html"
	});

	renderSets();
};

function getDate(datestr) {
	var year = datestr.substring(0, 4);
	var month = datestr.substring(5, 7);
	var day = datestr.substring(8, 10);
	var hour = datestr.substring(11, 13);
	var minute = datestr.substring(14, 16);
	return new Date(Date.UTC(year, month - 1, day, hour, minute, 0));
};

function renderSets() {
	$.ajax({
		type: "POST",
		url: "/get_sets",
		data: {}, //TODO -- restrict to sets which are in the current range
		success: function(data) {
			$("#set_list_div").html(data);
		},
		dataType: 'html'
	});
};

function saveComment(set_id, comment_text) {
	$.ajax({
		type: "POST",
		url: "/save_comment",
		data: {'set_id': set_id, 'comment_text': comment_text},
		success: function(data) {
			document.write(data);
		},
		dataType: 'html'
	});
};
