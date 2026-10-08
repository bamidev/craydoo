{
    'name': 'Craydoo Netherlands - Accounting',
    'version': '20.0.1.0.0',
    'summary': 'Dutch chart of accounts for the Craydoo suite',
    'description': """
Provides a `cd.account.chart` with the Dutch account codes/names, so it
can be applied onto a `cd.account.ledger` via the Craydoo Account chart
wizard.

The account codes and names are taken from Odoo's `l10n_nl` module,
originally authored by Onestein (https://www.onestein.eu).
""",
    'category': 'Accounting',
    'author': 'Craydoo',
    'license': 'LGPL-3',
    'depends': ['craydoo_account'],
    'data': [
        'data/account_chart_data.xml',
        'data/cd.account.chart.account-nl.csv',
        'data/account_chart_defaults.xml',
    ],
}
