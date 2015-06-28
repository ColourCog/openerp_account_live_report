{
    "name": "Accounting Live Reports",
    "version": "0.1",
    "category": "Accounting",
    "sequence": 60,
    "complexity": "normal",
    "author": "ColourCog.com",
    "website": "http://colourcog.com",
    "depends": [
        "base",
        "web",
        "account_accountant",
    ],
    "summary": "Generate realtime accounting reports",
    "description": """
Accounting Live Reports
=======================
This module creates computed accounting snapshots.

Features:
---------
* Profit/Loss
* Balance Sheet
    """,
    "data": [
      'report_view.xml',
    ],
    'css': [
        'static/src/css/live_wizard.css',
    ],
    'js': [
        'static/src/js/live_wizard.js',
    ],
    'qweb': [
        "static/src/xml/live_wizard.xml",
    ],
    "application": False,
    "installable": True
}
