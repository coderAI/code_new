function initMap() {
	//Location of user
	lat_value = parseFloat(document.getElementById('lat_value').value);
	long_value = parseFloat(document.getElementById('long_value').value);
	var myLatlng = {lat: lat_value, lng: long_value};
	
	cp_lat_value = parseFloat(document.getElementById('cp_lat_value').value);
	cp_long_value = parseFloat(document.getElementById('cp_long_value').value);
	var cp_lng = {lat: cp_lat_value, lng: cp_long_value};
	
//	is_updated = document.getElementById('is_updated').checked;
//	if (is_updated)
//		$(".toggler").trigger("click");
	
	
	//Location of flemington
	flem_lng = {lat: 10.763823355198488, lng: 106.65606066584587};
	
	this.geocoder = new google.maps.Geocoder();
	
	//Describe map
	this.map = new google.maps.Map(document.getElementById('map'), {
		  zoom: 10,
		  center: myLatlng,
		  disableDefaultUI: true
		});
	
	//Draw campus
	var cp_circle = new google.maps.Circle({
		strokeColor: '#000066',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: '#000066',
        fillOpacity: 0.35,
        center: cp_lng,
	    map: this.map,
	    radius: 200,
		});
	
	
//	var marker = new google.maps.Marker({
//	  position: myLatlng,
//	  map: map,
//	});
	
	//Get direction from user location to Flemington to get distance
	
	this.directionsToFlemService = new google.maps.DirectionsService();
	requestToFlem = {
			destination: flem_lng,
			origin: myLatlng,
			travelMode: google.maps.TravelMode.DRIVING
	};
	
	this.directionsToFlemService.route(requestToFlem, function(response, status) {
		if (status == google.maps.DirectionsStatus.OK) {
			var distance = response.routes[0].legs[0]['distance'].text;
			//Update distance to flemington
			document.getElementById('distance_to_flem').value = distance;
		}
		});
	
	
	//Draw direction
	this.directionsDisplay = new google.maps.DirectionsRenderer({
		map: this.map
	});
	
	// Pass the directions request to the directions service.
	this.directionsService = new google.maps.DirectionsService();
	
	// Set destination, origin and travel mode.
	request = {
			destination: cp_lng,
			origin: myLatlng,
			travelMode: google.maps.TravelMode.DRIVING
	};
	
	
	this.directionsService.route(request, function(response, status) {
	if (status == google.maps.DirectionsStatus.OK) {
		// Display the route on the map.
		this.directionsDisplay.setDirections(response);
		
		update_map_info(response);
	}
	});
	
	//Redraw marker when click on map
	google.maps.event.addListener(this.map, 'click', function(args) {  
        console.log('lat', args.latLng.lat(),'lng=',args.latLng.lng());
        lat_value = args.latLng.lat();
        long_value = args.latLng.lng();
		
		document.getElementById('lat_value').value = lat_value.toString();
		document.getElementById('long_value').value = long_value.toString();
		
		myLatlng = {lat: lat_value, lng: long_value}; 
		
		if (args.call_outside == undefined){
			self.geocoder.geocode( { 'location': myLatlng}, function(results, status) {
				start_address = results[0].formatted_address;
				document.getElementById('origin_address').value = start_address;
				document.getElementById('origin_address_default').value = start_address;
			});
		}
		
		
		//Update origin of direction
		request.origin = myLatlng;
		
		//Update distance to Flemington from new address
		requestToFlem.origin = myLatlng;
		directionsToFlemService.route(requestToFlem, function(response, status) {
			if (status == google.maps.DirectionsStatus.OK) {
				var distance = response.routes[0].legs[0]['distance'].text;
				//Update distance to flemington
				document.getElementById('distance_to_flem').value = distance;
			}
			});
		
		directionsService.route(request, function(response, status) {
		if (status == google.maps.DirectionsStatus.OK) {
			// Display the route on the map.
			this.directionsDisplay.setDirections(response);
			
			update_map_info(response);
		}
		});
		
    });
	
	
	function update_map_info(response){
		try{
//			var start_address = response.routes[0].legs[0]['start_address'];
			var distance = response.routes[0].legs[0]['distance'].text;
			
			var distance_to_flem = document.getElementById('distance_to_flem').value;
//			
			document.getElementById('map_info').innerHTML = "Khoảng cách đến Campus là &nbsp;&nbsp;<span style='font-style:italic;color:#ff3300'>"+ distance + " </span> "  +
															"<br>" +
															"Khoảng cách đến &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style='font-style:italic;color:#ff3300'>" + distance_to_flem + " </span> ";
		}
		catch(err){
			console.log("Can not render address and distance");
			console.log(err);
		}
	}
	
	
};

function codeAddress() {
	var address = document.getElementById("origin_address").value;
	
	
	
	this.geocoder.geocode( { 'address': address}, function(results, status) {
	  if (status == google.maps.GeocoderStatus.OK) {
		data = {latLng: results[0].geometry.location, 'call_outside': true}  
		
//		console.log('data lat', data.latLng.lat(),'lng=',data.latLng.lng());
		
		start_address = results[0].formatted_address;
		document.getElementById('origin_address').value = start_address;
		document.getElementById('origin_address_default').value = start_address;
		
		google.maps.event.trigger( this.map, 'click', data );
		
	  } else {
	    alert("Geocode was not successful for the following reason: " + status);
	  }
	});
  }




//Side panel

$.fn.BootSideMenu = function( options ) {

	var oldCode, newCode, side;

	newCode = "";

	var settings = $.extend({
		side:"left",
		autoClose:true
	}, options );

	side = settings.side;
	autoClose = settings.autoClose;

	this.addClass("container sidebar");

	if(side=="left"){
		this.addClass("sidebar-left");
	}else if(side=="right"){
		this.addClass("sidebar-right");
	}else{
		this.addClass("sidebar-left");	
	}

	oldCode = this.html();

	newCode += "<div class=\"row\">\n";
	newCode += "	<div class=\"col-xs-12 col-sm-12 col-md-12 col-lg1-12\" data-side=\""+side+"\">\n"+ oldCode+" </div>\n";
	newCode += "</div>";
	newCode += "<div class=\"toggler\">\n";
	newCode += "	<span class=\"glyphicon glyphicon-chevron-right\">&nbsp;</span> <span class=\"glyphicon glyphicon-chevron-left\"  style=\'display:block\'>&nbsp;</span>\n";
	newCode += "</div>\n";

	//Mod suggested by asingh3
	//https://github.com/AndreaLombardo/BootSideMenu/issues/1
	
	//this.html(newCode);

		var wrapper = $(newCode);
	// copy the children to the wrapper.
	$.each(this.children(), function () {
		$('.panel-content', wrapper).append(this);
	});

	// Empty the element and then append the wrapper code.
	$(this).empty();
	$(this).append(wrapper);

	if(autoClose){
		$(this).find(".toggler").trigger("click");
	}

};


$(document).on('click','.toggler', function(){
	var toggler = $(this);
	var container = toggler.parent();
	var listaClassi = $(container[0]).attr('class').split(/\s+/); //IE9 Fix - Thanks Nicolas Renaud
	var side = getSide(listaClassi);
	var containerWidth = container.width();
	var status = container.attr('data-status');
	if(!status){
		status = "opened";
	}
	doAnimation(container, containerWidth, side, status);
});

/*Cerca un div con classe submenu e id uguale a quello passato*/
//function searchSubMenu(id){
//	var found = false;
//	$('.submenu').each(function(){
//		var thisId = $(this).attr('id');
//		if(id==thisId){
//			found = true;
//		}
//	});
//	return found;
//}
//Get sidebar (left/right) base on class of sidebar
function getSide(listaClassi){
	var side;
	for(var i = 0; i<listaClassi.length; i++){
		if(listaClassi[i]=='sidebar-left'){
			side = "left";
			break;
		}else if(listaClassi[i]=='sidebar-right'){
			side = "right";
			break;
		}else{
			side = null;
		}
	}
	return side;
}

//do Animation
function doAnimation(container, containerWidth, sidebarSide, sidebarStatus){
	var toggler = container.children()[1];
	if(sidebarStatus=="opened"){
		if(sidebarSide=="left"){
			container.animate({
				left:-(containerWidth+2)
			},{duration: 200});
			toggleArrow(toggler, "left");
		}else if(sidebarSide=="right"){
			container.animate({
				right:- (containerWidth +2)
			},{duration: 200});
			toggleArrow(toggler, "right");
		}
		container.attr('data-status', 'closed');
	}else{
		if(sidebarSide=="left"){
			container.animate({
				left:0
			},{duration: 200});
			toggleArrow(toggler, "right");
		}else if(sidebarSide=="right"){
			container.animate({
				right:0
			},{duration: 200});
			toggleArrow(toggler, "left");
		}
		container.attr('data-status', 'opened');
	
	}

}

function toggleArrow(toggler, side){
	if(side=="left"){
		$(toggler).children(".glyphicon-chevron-right").css('display', 'block');
		$(toggler).children(".glyphicon-chevron-left").css('display', 'none');
	}else if(side=="right"){
		$(toggler).children(".glyphicon-chevron-left").css('display', 'block');
		$(toggler).children(".glyphicon-chevron-right").css('display', 'none');
	}
}

function onWindowResize() {
 $(".toggler").each( function(){
	var container = $(this).parent();
	var listaClassi = $(container[0]).attr('class').split(/\s+/); 
	var side = getSide(listaClassi);
	
	var status = container.attr('data-status');
	var containerWidth = container.width();
	if (status==="closed") {
		if(side=="left"){
			container.css("left",-(containerWidth+2))

		}else if(side=="right"){
			container.css("right",-(containerWidth+2))

		}
	}
})
}
window.addEventListener('resize', onWindowResize, false);


$(document).ready(function(){
    $('#side_panel').BootSideMenu({side:"left", autoClose:false});
    $("#origin_address").keyup(function(event){
        if(event.keyCode == 13){
        	codeAddress();
        }
    });
    
});