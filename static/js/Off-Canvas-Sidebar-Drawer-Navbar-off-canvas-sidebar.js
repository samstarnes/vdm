/**
The Ultimate Bootstrap Studio Bootstrap 4 Off-Canvas Sidebar/Drawer Navbar

This component uses 100% bootstrap studio supported components - NO CUSTOM CODE. While reading this, be aware I call this component a "drawer". 

By default, I have the drawer set to open. Just set the data-open-drawer attribute on the Navbar to 0 for "normal" functionality.

There are a number of specific css classes you need to be aware of, but for the most part, you can use this simply by dropping it into your project. It all starts at the top level with a standard Navbar component. If you select that, you will see a "data-open-drawer" attribute that you can set to 1 to show the nav bar for development purposes. While open, customize it for your needs. As is, there is a brand heading and close button on the top. Then a dynamic height middle nav that will scroll within itself if it becomes too long. Lastly there is a fixed bottom nav which can be entirely removed without causing any issues if you don't need it. There is also a predefined "open drawer" button that can be easily adjusted or removed without causing any issues.

The Navbar should be set to be fluid and have a position of "Fixed to top". It also requires my added class of "off-canvas".

Things you will probably want or need to change in the css file (off-canvas-sidebar.css): the default opening button settings and responsive drawer widths. Most of that is near the bottom of the file. Honestly, that's about it... unless you run into trouble with some z-index stuff... but my usage of that is very light.

The CSS file was created to do only what was needed to enforce the drawer's functionality. It doesn't do much of anything for visual styles like coloring and such. You can use the standard bootstrap studio controls to change the colors and everything else mostly. Though, I would recommend caution when messing with flex settings or responsive display stuff... but if you mess it up in the editor, going back to default should fix it and reset things to what the css file specifies.

In my development version, the CSS file is organized into 5 sections. Section 1 and 2 are responsible for the core settings to make the drawer work accordingly. Section 3 is where you can change the settings of the default "open drawer" button - I call it a "drawer knob". Section 4 is for setting the drawer width per responsive breakpoint. And Section 5 is an advanced section focused on expanding on the default functionality of this component. It provides CSS so that with a few extra divs and classes, you can change how the drawer "slides" onto your page - it can be over top of the site, push the site, slide the site. Also in that section, I had instruction on how to use more included CSS with just one added div to fade your site's content while the drawer is open. I will provide all of that documentation here in a moment.

There are 2 included JavaScript files with this component: swipe.js and off-canvas-sidebar.js (this file). The swipe.js file contains a simple and clean implementation of pure javascript swipe event detection (mostly for mobile devices). I did not write that code - as stated at the top of that file. I did write the off-canvas-sidebar.js (this) file to provide simple interaction support for opening and closing your drawers. It allows you to place anything on your site anywhere with attributes of data-open="drawer", data-dismiss="drawer", and/or data-toggle="drawer" to automatically add click/touch support to those items to open, close, or toggle the drawer, respectively.

Those data-* attributes can also be set to left-drawer or right-drawer in the event you have multiple drawers and need more specific control.

IMPORTANT: JS FILE ORDER MATTERS - make sure swipe.js is included before off-canvas-sidebar.js. To do that, right click the JavaScript category header in your design tab (bottom right) and select "Include Order...".

*** If you want the drawer to be open on load, you will need to be sure to add the "open" class to the navbar (and you should also add "open" to site wrapper if you are using the dom and css from the slide or push styles detailed in section 5 notes). If you are using the fade feature, you will also need to add the class "drawer-open" to the body tag.

*** If you want the drawer on the right side, you need to set the "data-right-drawer" attribute on the Navbar to 1 or add the class "right-drawer" to the Navbar. In this current version, the Right Drawers don't work with slide and push styles. Sorry for any inconvenience.

Thank you for using my component. I hope you like it and that it helps you out. If you have any feedback or problems, you can try to reach me on Twitter: @evileyegames


SECTION NOTES:

SECTION 1: Basic settings to create the off-canvas drawer menu
    All the basic and require settings for the drawer (left and right)
    
SECTION 2: Handle auto open points from "Expanded" setting
    Adds support to make the Navbar's Expanded setting auto open the drawer and make it uncloseable at the specific responsive breakpoint. See notes in section 5 about using this feature with other drawer styles.
    
SECTION 3: Drawer knob/opener button
    Provides the ability to change how and where the default "drawer knob" is rendered (if you are using it)
    
SECTION 4: Responsive drawer menu widths
    Sets the widths of the drawer for each responsive breakpoint.
    
SECTION 5: ADVANCED - Drawer on page style (overlay, push, slide) and optional content fade
    Everything in this section requires additional and specific dom elements to be added beyond the component's default and provided structure; as is, the "style" being used by default is called overlay. The required dom for each style is provided with their notes below. The reason these additional things are provided is to make it easier to use different drawer types and formats.
    
    IMPORTANT NOTE ABOUT SIZES: if you changed the default nav width in the CSS refered to as Section 4 and are using any style other than the default (overlay), you will need to update various sizes in the CSS code in section 5 to match the width you set on your nav for each responsive breakpoint.
    
    MISSING FUNCTIONALITY: for now, I've not added support for the push or slide styles to work with right-side nav drawers. Maybe I will someday... but not for now. Sorry!
    
    
    STYLE NOTES:
    
    ~~OVERLAY~~ the default style; the menu simply slides in over top of the site
    
    
    ~~PUSH~~ pushes the main site body along with the drawer, condensing the site body's space
    required DOM: <div class="drawer-push"><ThisNavBarComponent/><div class="drawer-site">Site Content</div></div>
    
    IMPORTANT NOTE: if you use an "Expanded" setting on the navbar, add the expand class to the drawer-push div's class set, but replace the term "navbar" in the class name with "drawer". For example: navbar with navbar-expand-lg should have a parent with drawer-push AND drawer-expand-lg classes.
    
    
    ~~SLIDE~~ pushes the main site body off the screen along with the drawer
    required DOM: <div class="drawer-slide"><ThisNavBarComponent/><div class="drawer-site">Site Content</div></div>
    
    IMPORTANT NOTE: this style is not coded to work with the "Expanded" navbar setting. When content is slid off screen, it becomes inaccessible; so it makes no sense to have a screen size that always makes this content inaccessible. To use the SLIDE style, set "Expanded" to Never.
    
    
    ~~FADE CONTENT~~ fades the main site content while the drawer is open; this does work with all drawer styles
    to make this work, just add an empty div with a class of "drawer-fade" directly in your body tag: <body><div class="drawer-fade"></div><EverythingElse></body>
    
    IT'S A FEATURE, NOT A BUG: while the fade feature works with all nav styles, it will NOT open if you use the "Expanded" setting while at the "Expanded" point. This is intentional. The "Expanded" setting is used to have your nav show all the time at and above a specific breakpoint. If the nav is always showing AND the fade is displayed, the site's content will always be covered - faded out and inaccessible... which I don't see ever being a desired effect.
    
    ONE BUG (sorta): you can technically cause your site to be inaccessible. This feature works using a class set on the body to indicate that the drawer is open. That class is only set via JavaScript when the menu is opened. Technically, if you set the drawer to always be open with the "Expanded" setting and shrink your screen below that point to allow yourself to open it via JavaScript, then re-expand your window... you will have the open class on your body tag causing the fade to be rendered but the close-menu option will have disappeared, so there is no way to remove the class... aside from re-shrinking your screen. I hate to say "just don't do that" but I do feel this is a slim edge case and "fixing" it would be more work than it is worth in my opinion... for now at least. The fix would require another manual setting of the "Expanded" setting on the fade div or even the body tag. Perhaps I'll come back and add that some day.
**/

let isOpen = function(drawer) {
    return drawer.attr('data-open-drawer') == '1' || drawer.hasClass('open');
},
anyOpenDrawers = function () {
    let anyOpen = false;
    $('.navbar.fixed-top.off-canvas').each(function(){
        if (isOpen($(this)))
        {
            anyOpen = true;
            return false;
        }
    });
    
    return anyOpen;
},
openDrawer = function(drawer) {
    if (!isOpen(drawer))
    {
        if (!anyOpenDrawers())
        {
            let p = drawer.parent();
            if (p.hasClass('drawer-push') || p.hasClass('drawer-slide'))
                p.addClass('open');
            $('body').addClass('drawer-open');
        }
        
        drawer.addClass('open').attr('data-open-drawer', '1');
    }
}, 
closeDrawer = function(e, drawer) {
    if (typeof drawer === 'undefined')
    {
        drawer = $('.navbar.fixed-top.off-canvas.open');
        if (drawer.length === 0)
            drawer = $('.navbar.fixed-top.off-canvas[data-open-drawer="1"]');
    }
    
    let p = drawer.parent();
    drawer.removeClass('open');
    drawer.attr('data-open-drawer', '0');
    
    if (!anyOpenDrawers())
    {
        if (p.hasClass('drawer-push') || p.hasClass('drawer-slide'))
            p.removeClass('open');
        $('body').removeClass('drawer-open');
    }
    
},
getRightDrawer = function() {
    let d = $('.navbar.fixed-top.off-canvas.right-drawer');
    if (d.length === 0)
        d = $('.navbar.fixed-top.off-canvas[data-right-drawer="1"]');
    if (d.length === 0)
        d = null;
    return d;
},
getLeftDrawer = function() {
    let d = $('.navbar.fixed-top.off-canvas:not(.right-drawer)');
    if (d.length === 0)
        return null;
    
    let ld = null;
    d.each(function() {
        if (typeof d.attr('data-right-drawer') === 'undefined' || d.attr('data-right-drawer') == '0')
        {
            ld = d;
            return false;
        }
    });

    return ld;
},
toggleDrawer = function(drawer) {
    if (isOpen(drawer))
        closeDrawer(drawer);
    else
        openDrawer(drawer);
};

$(document).on('click touch', '[data-dismiss="drawer"]', {}, closeDrawer);

$(document).on('click touch', '[data-dismiss="left-drawer"]', {}, function(e) {
    closeDrawer(e, getLeftDrawer());
});

$(document).on('click touch', '[data-dismiss="right-drawer"]', {}, function(e) {
    closeDrawer(e, getRightDrawer());
});

$(document).on('click touch', '[data-open="drawer"]', {}, function() {
    openDrawer($('.navbar.fixed-top.off-canvas:not(.open)'));
});

$(document).on('click touch', '[data-open="left-drawer"]', {}, function() {
    openDrawer(getLeftDrawer());
});

$(document).on('click touch', '[data-open="right-drawer"]', {}, function() {
    openDrawer(getRightDrawer());
});

$(document).on('click touch', '[data-toggle="drawer"]', {}, function() {
    toggleDrawer($('.navbar.fixed-top.off-canvas'));
});

$(document).on('click touch', '[data-toggle="left-drawer"]', {}, function() {
    toggleDrawer(getLeftDrawer());
});

$(document).on('click touch', '[data-toggle="right-drawer"]', {}, function() {
    toggleDrawer(getRightDrawer());
});

swipeDetect($(document)[0], function(dir) {
    let leftDrawer = getLeftDrawer(),
        rightDrawer = getRightDrawer();
    
    if (dir === 'left')
    {
        // close left drawer
        if (leftDrawer.length > 0 && isOpen(leftDrawer))
        {
            closeDrawer(leftDrawer);
        }
        // open right drawer
        else if (rightDrawer.length > 0)
        {
            openDrawer(rightDrawer);
        }
    }
    else if (dir === 'right')
    {
        // close right drawer
        if (rightDrawer.length > 0 && isOpen(rightDrawer))
        {
            closeDrawer(rightDrawer);
        }
        // open left drawer
        else if (leftDrawer.length > 0)
        {
            openDrawer(leftDrawer);
        }
    }
});