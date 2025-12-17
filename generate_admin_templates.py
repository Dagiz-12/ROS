"""
Generate remaining admin panel templates quickly
"""

templates = {
    'table_management.html': {
        'title': 'Table Management - Admin Panel',
        'icon': 'fa-table',
        'sections': ['Table Layout', 'QR Codes', 'Capacity Management']
    },
    'analytics.html': {
        'title': 'Analytics Dashboard - Admin Panel',
        'icon': 'fa-chart-line',
        'sections': ['Sales Analytics', 'Customer Insights', 'Performance Metrics']
    },
    'reports.html': {
        'title': 'Reports - Admin Panel',
        'icon': 'fa-file-alt',
        'sections': ['Sales Reports', 'Inventory Reports', 'Staff Reports']
    }
}

for filename, config in templates.items():
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config['title']}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-lg">
        <div class="container mx-auto px-4 py-3">
            <div class="flex justify-between items-center">
                <div class="flex items-center space-x-3">
                    <a href="{{% url 'admin-dashboard' %}}" class="text-gray-600 hover:text-red-600">
                        <i class="fas fa-arrow-left"></i>
                    </a>
                    <i class="fas {config['icon']} text-2xl text-red-600"></i>
                    <div>
                        <h1 class="text-xl font-bold">{config['title'].split(' - ')[0]}</h1>
                        <p class="text-sm text-gray-600">{{{{ restaurant.name|default:"Restaurant" }}}}</p>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <span class="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full">{{{{ user_role|title }}}}</span>
                </div>
            </div>
        </div>
    </nav>

    <div class="container mx-auto px-4 py-6">
        <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-bold mb-6">Under Development</h2>
            <div class="text-center py-12 text-gray-500">
                <i class="fas {config['icon']} text-4xl mb-4"></i>
                <p class="text-xl mb-2">{config['title'].split(' - ')[0]} is coming soon!</p>
                <p class="text-gray-600">This section is currently under development.</p>
                <div class="mt-6 p-4 bg-gray-100 rounded-lg max-w-md mx-auto text-left">
                    <p class="font-medium mb-2">Planned features:</p>
                    <ul class="list-disc pl-5 space-y-1">
                        {''.join([f'<li>{section}</li>' for section in config['sections']])}
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Placeholder for future functionality
        console.log('{filename} loaded');
    </script>
</body>
</html>"""

    with open(f'admin_panel/templates/admin_panel/{filename}', 'w') as f:
        f.write(html)
    print(f'Created: templates/admin_panel/{filename}')

print("All admin templates created!")
