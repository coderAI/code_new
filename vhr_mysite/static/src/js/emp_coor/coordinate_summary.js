function initMap() {
	var myLatlng = {lat: 10.804070141719273, lng: 106.69310512542725};
	
	this.map = new google.maps.Map(document.getElementById('map'), {
	  zoom: 12,
	  center: myLatlng,
	  disableDefaultUI: true
	});
	window.map = this.map;
	
}