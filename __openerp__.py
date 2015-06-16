{
    "name" : "Accounting Live Reports",
    "version" : "0.1",
    "category" : "Accounting",
    "sequence": 60,
    "complexity" : "normal",
    "author" : "ColourCog.com",
    "website" : "http://colourcog.com",
    "depends" : [
        "base",
        "account_accountant",
    ],
    "summary" : "Generate realtime accounting reports",
    "description" : """
Accounting Live Reports
=======================
This module creates computed accounting snapshots.

Features:
---------
* Profit/Loss
* Balance Sheet
    """,
    'js': [
        'static/src/js/live_wizard.js',
    ],
    'qweb' : [
        "static/src/xml/live_wizard.xml",
    ],
    "data" : [
      'report_view.xml',
    ],
    "application": False,
    "installable": True
}

