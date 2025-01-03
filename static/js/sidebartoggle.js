document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.m-sidebar');
    const navbarToggler = document.querySelector('.navbar-toggler');
    const mGrid = document.querySelector('.m-grid');
    const divNav = document.querySelector('.divnav'); // Select the divnav element

    // Function to adjust top margin and toggle button position based on navbar height
    function adjustTopMarginAndTogglePosition() {
        setTimeout(() => {
            const navbarHeight = document.querySelector('nav.navbar').offsetHeight;
            mGrid.style.marginTop = navbarHeight + 'px';
            divNav.style.marginTop = navbarHeight + 'px'; // Adjust divnav margin-top as well
            sidebarToggle.style.top = navbarHeight + 'px'; // Adjust sidebarToggle position as well
        }, 350); // Adjust timeout to match your CSS transition duration
    }

    // Toggle sidebar visibility
    sidebarToggle.addEventListener('click', function() {
        const isOpen = sidebar.style.left === '0px';
        sidebar.style.left = isOpen ? '-250px' : '0px';
        if (isOpen) {
            sidebarToggle.classList.remove('open');
        } else {
            sidebarToggle.classList.add('open');
        }
    });

    // Adjust top margin and toggle position on navbar toggle click
    navbarToggler.addEventListener('click', function() {
        adjustTopMarginAndTogglePosition();
    });

    // Initial adjustment in case the page loads with the navbar already toggled
    adjustTopMarginAndTogglePosition();

    // Re-adjust when window is resized
    window.addEventListener('resize', adjustTopMarginAndTogglePosition);
});
