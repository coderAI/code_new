/* ------------------------------------------------------------------------
Class: freezeHeaderMonthlyCalendar
Use:freeze header row in html table
Example 1:  $('#tableid').freezeHeaderMonthlyCalendar();
Example 2:  $("#tableid").freezeHeaderMonthlyCalendar({ 'height': '300px' });
Example 3:  $("table").freezeHeaderMonthlyCalendar();
Example 4:  $(".table2").freezeHeaderMonthlyCalendar();
Author(s): Laerte Mercier Junior, Larry A. Hendrix
Version: 1.0.6
-------------------------------------------------------------------------*/
(function ($) {
    var TABLE_ID = 0;
    $.fn.freezeHeaderMonthlyCalendar = function (params) {

        var copiedHeader = false;

        function freezeHeaderMonthlyCalendar(elem) {
            var idObj = elem.attr('id') || ('tbl-' + (++TABLE_ID));
            
            // Get the height of extra blocks
            var search_heigh1 = $(".oe_searchview_drawer").outerHeight();
            var quickadd_heigh = $(".toolbar").outerHeight();
            
            // By defaul turn on the visible mode
            var search_visible = true;
            var quickadd_visible = true;
            
            // Check visible mode
            if (!$(".oe_searchview_drawer").is(":visible")) {
            	search_visible = false;
            }
            if (!$(".toolbar").is(":visible")) {
            	quickadd_visible = false;
            }
            
            var origin_position = elem.position();
            var origin_top = origin_position ? origin_position.top : 0;
            
            var origin_height = 0
            
            if (elem.length > 0 && elem[0].tagName.toLowerCase() == "table") {

                var obj = {
                    id: idObj,
                    grid: elem,
                    container: null,
                    header: null,
                    divScroll: null,
                    openDivScroll: null,
                    closeDivScroll: null,
                    scroller: null
                };

                if (params && params.height !== undefined) {
                    obj.divScroll = '<div id="hdScroll' + obj.id + '" style="height: ' + params.height + '; overflow-y: scroll">';
                    obj.closeDivScroll = '</div>';
                    
                    origin_height = parseInt(params.height);
                }

                obj.header = obj.grid.find('thead');

                if (params && params.height !== undefined) {
                    if ($('#hdScroll' + obj.id).length == 0) {
                        obj.grid.wrapAll(obj.divScroll);
                    }
                }

                obj.scroller = params && params.height !== undefined
                   ? $('#hdScroll' + obj.id)
                   : $(window);

                if (params && params.scrollListenerEl !== undefined) {
                    obj.scroller = params.scrollListenerEl;
                }
                
                var select_all = $('th input.oe_list_record_selector');
                
                obj.scroller.on('scroll', function () {
                    if ($('#hd' + obj.id).length == 0) {
                        obj.grid.before('<div id="hd' + obj.id + '"></div>');
                    }

                    obj.container = $('#hd' + obj.id);

                    if (obj.header.offset() != null) {
                        if (limiteAlcancado(obj, params)) {
                            if (!copiedHeader) {
                                cloneHeaderRow(obj);
                                copiedHeader = true;
                            }
                        }
                        else {
                            if (($(document).scrollTop() > obj.header.offset().top)) {
                                obj.container.css("position", "absolute");
                                obj.container.css("top", (obj.grid.find("tr:last").offset().top - obj.header.height()) + "px");
                            }
                            else {
                                obj.container.css("visibility", "hidden");
                                obj.container.css("top", "0px");
                                obj.container.width(0);
                            }
                            copiedHeader = false;
                        }
                    }
                    cloneHeaderRow(obj);
                    var pos = obj.scroller.scrollTop();
                    if (pos == 0) {
                    	obj.container.css("visibility", "hidden");
                    } else {
                    	obj.container.css("visibility", "visible");
                    	obj.container.css("z-index", "1");
                    }
                    
                	var exchange_top = origin_top;
                	var exchange_height = origin_height;
                	var exchange_search = 0;
                	
                	// Re-caculate the height of extra blocks
                    var search_heigh2 = $(".oe_searchview_drawer").outerHeight();
                    quickadd_heigh = $(".toolbar").outerHeight();
                	
                	// Check search block
                	if (search_visible) {
                		if (!$(".oe_searchview_drawer").is(":visible")) {
                			exchange_top -= search_heigh2;
                		}
                		exchange_search = search_heigh2 - search_heigh1;
                	} else {
                		if ($(".oe_searchview_drawer").is(":visible")) {
                			exchange_top += search_heigh2;
                		}
                	}
                	
                	// Check quickadd block
                	if (quickadd_visible) {
                		if (!$(".toolbar").is(":visible")) {
                			exchange_top -= quickadd_heigh;
                		}
                	} else {
                		if ($(".toolbar").is(":visible")) {
                			exchange_top += quickadd_heigh;
                		}
                	}
                	
                	// Fix height
                	exchange_height = origin_height + origin_top - exchange_top - exchange_search;
                	exchange_top +=  exchange_search;
                	obj.container.css("top", exchange_top.toString() + "px");
                	
                	// Always margin-bottom 7px for the vertical scroll bar
                	exchange_height -= 8;
                	
                	obj.scroller.css("height", exchange_height.toString() + "px");

                	$('div[id^="hdScroll"] .new_oe_list_record_selector').prop(select_all.prop('checked') || false);
                	
                	$('div[id^="hdScroll"] .new_oe_list_record_selector').on('click', function(e) {
                		
                		if (select_all.prop('checked') && !$(this).prop('checked')) {
                			select_all.prop('checked', false);
                		} else if (!select_all.prop('checked') && $(this).prop('checked')) {
                			select_all.prop('checked', true);
                		}
                		select_all.trigger("click");
            			
            			var check = $('div[id^="hdScroll"]').find('.oe_list_record_selector input').prop('checked');
            			select_all.prop('checked', check);
                    });
                	
                	obj.scroller.width(obj.scroller.width() >= obj.container.width() ? obj.scroller.width() : obj.container.width() +80);
                	obj.scroller.css("overflow-x", "hidden");
                });
            }
        }

        function limiteAlcancado(obj, params) {
            if (params && (params.height !== undefined || params.scrollListenerEl !== undefined)) {
                return (obj.header.offset().top <= obj.scroller.offset().top);
            }
            else {
                return ($(document).scrollTop() > obj.header.offset().top && $(document).scrollTop() < (obj.grid.height() - obj.header.height() - obj.grid.find("tr:last").height()) + obj.header.offset().top);
            }
        }

        function cloneHeaderRow(obj) {
            obj.container.html('');
            obj.container.val('');
            var tabela = $('<table style="margin: 0 0;"></table>');
            var atributos = obj.grid.prop("attributes");

            $.each(atributos, function () {
                if (this.name != "id") {
                    tabela.attr(this.name, this.value);
                }
            });
            
            obj.header.clone().appendTo(tabela);

            obj.container.append(tabela);
            obj.container.width(obj.header.outerWidth());
            obj.container.height(obj.header.outerHeight());
            obj.container.find('th').each(function (index) {
                var cellWidth = obj.grid.find('th').eq(index).outerWidth();
                $(this).css('width', cellWidth);
                if ($(this).find('.oe_list_record_selector').length) {
                	$(this).find('.oe_list_record_selector').addClass('new_oe_list_record_selector').removeClass('oe_list_record_selector');
                }
            });

            obj.container.css("visibility", "visible");

            if (params && params.height !== undefined) {
            	obj.container.css("top", "0px");
                obj.container.css("position", "absolute");
            } else if (params && params.scrollListenerEl!== undefined) { 
            	obj.container.css("top", "0px");
                obj.container.css("position", "absolute");
                obj.container.css("z-index", "2");
            } else {
                obj.container.css("top", "0px");
                obj.container.css("position", "fixed");
            }
        }

        return this.each(function (i, e) {
            freezeHeaderMonthlyCalendar($(e));
        });

    };
})(jQuery);
