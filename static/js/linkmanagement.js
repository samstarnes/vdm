const contentMap = {
    "User Management": {
        tc1: "Content for TC1 from User Management",
        tc2: "Content for TC2 from User Management",
        tc3: "Content for TC3 from User Management",
        tc4: "Content for TC4 from User Management"
    },
    "Content Manager": {
        tc1: "<h1>Move Storage</h1>",
        tc2: "<input id='bdir' value='{{ bdir }' type='text' readonly disabled />",
        tc3: "<div class='table-responsive'><table class='table'><thead><tr><th>Service</th><th>Port</th></tr></thead><tbody><tr><td>YTDL</td><td>{{ docker_port_ytdl }}</td></tr><tr><td>YTDLDB</td><td>{{ docker_port_ytdldb }}</td></tr><tr><td>Redis</td><td>{{ docker_port_ytdlredis }}</td></tr><tr><td>MeiliSearch</td><td>{{ docker_port_ytdlmeili }}</td></tr></tbody></table></div>",
        tc4: "Content for TC4 from Content Manager"
    },
    "Console and Scripts": {
        tc1: "Content for TC1 from Console and Scripts",
        tc2: "Content for TC2 from Console and Scripts",
        tc3: "Content for TC3 from Console and Scripts",
        tc4: "Content for TC4 from Console and Scripts"
    },
    "Backup and Restore": {
        tc1: "Content for TC1 from Backup and Restore",
        tc2: "Content for TC2 from Backup and Restore",
        tc3: "Content for TC3 from Backup and Restore",
        tc4: "Content for TC4 from Backup and Restore"
    },
    "Analytics and Reports": {
        tc1: "Content for TC1 from Analytics and Reports",
        tc2: "Content for TC2 from Analytics and Reports",
        tc3: "Content for TC3 from Analytics and Reports",
        tc4: "Content for TC4 from Analytics and Reports"
    },
    "System Status and Logs": {
        tc1: "Content for TC1 from System Status and Logs",
        tc2: "Content for TC2 from System Status and Logs",
        tc3: "Content for TC3 from System Status and Logs",
        tc4: "Content for TC4 from System Status and Logs"
    },
    "Security Logs": {
        tc1: "Content for TC1 from Security Logs",
        tc2: "Content for TC2 from Security Logs",
        tc3: "Content for TC3 from Security Logs",
        tc4: "Content for TC4 from Security Logs"
    },
};

document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default link action
            // Get the link text to use as a key in the contentMap
            const linkText = link.textContent.trim();
            // Retrieve the content mapping for the clicked link
            const content = contentMap[linkText];
            // Update each tc paragraph with the mapped content
            if (content) {
                for (let i = 1; i <= 4; i++) {
                    const paragraph = document.getElementById(`tc${i}`);
                    if (paragraph) {
                        paragraph.innerHTML = content[`tc${i}`];
                    }
                }
            }
        });
    });
});