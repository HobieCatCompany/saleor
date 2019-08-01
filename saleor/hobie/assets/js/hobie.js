// On scroll: shrink main header/nav & show/hide "where to buy" pop-up footer tab
$(document).ready(function() {
    // Get header/nav bar height on page load
    var header_height = $('header').height();
    $(window).scroll(function() {
        // When page scrolls past the height of the header/nav bar init shrink mode & show where to buy footer tab
        if ($(document).scrollTop() > header_height) {
            $('header').addClass('fixed-top shrink animated slideInDown');
            $('#where-to-buy-tab').removeClass('d-none').addClass('animated slideInUp');
        }
        // Return things to normal once the page is scrolled back to top
        else {
            $('header').removeClass('fixed-top shrink animated slideInDown');
            $('#where-to-buy-tab').addClass('d-none').removeClass('animated slideInUp');
        }
    });
});

// Make Bootstrap's dropdown component multi-level aware (i.e. can contain sub-menus or sub-sub-menus)
$('.dropdown-menu a.dropdown-toggle').on('click', function() {
    if (!$(this).next().hasClass('show')) {
        $(this).parents('.dropdown-menu').first().find('.show').removeClass('show');
    }
    var $subMenu = $(this).next('.dropdown-menu');
    $subMenu.toggleClass('show');
    $(this).parents('li.nav-item.dropdown.show').on('hidden.bs.dropdown', function() {
        $('.dropdown-submenu .show').removeClass('show');
    });
    return false;
});
