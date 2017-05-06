
$(document).ready(function() {
	
	$('#employee_search').typeahead({
	    source: function (query, process) {
	        return $.getJSON(
	            '/allowance/employee/list',
	            { query: query },
	            function (data) {
	                var newData = [];
	                $.each(data, function(){
	                    newData.push(this.name_related +  ' (' + this.login + ')');
	                });
	                return process(newData);
	            }); 
	    }
	});
	
	//auto hide when is not decision
	$('.decision_group').hide();
	$('#has_decision').change(function(){
		if ($(this).is(":checked")){
			$('.decision_group').show();			
	    }else{
	    	$('.decision_group').hide();	    	
	    }
	});
	
});	