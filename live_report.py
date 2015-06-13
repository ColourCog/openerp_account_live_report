# -*- coding: utf8 -*-
# live_report.py

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp


class account_live_line(osv.osv_memory):
    """
    Profit/Loss line
    """
    _name = "account.live.line"
    _description = "Account Live line"

    def _get_amounts(self, cr, uid, ids, name, args, context=None):
        """
        Compute amounts for account during period
        """
        line_obj = self.pool.get('account.move.line')
        res = {}
        for live in self.browse(cr, uid, ids, context=context):
            res[live.id] = {
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0
            }
            line_ids = line_obj.search(cr, uid, [("account_id", "=", live.account_id.id), ("period_id", "=", live.period_id.id)])
            lines = line_obj.browse(cr, uid, line_ids)
            for line in lines:
                res[live.id]['credit'] += line.credit
                res[live.id]['debit'] += line.debit
            res[live.id]['balance'] = res[live.id]['debit'] - res[live.id]['credit']
        return res


    _colums = {
        "name": fields.char("Account"),
        "account_id": fields.many2one('account.account', 'Account', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True),
        'credit': fields.function(_get_amounts, digits_compute=dp.get_precision('Account'), string='Credit'),
        'debit': fields.function(_get_amounts, digits_compute=dp.get_precision('Account'), string='Debit'),
        'balance': fields.function(_get_amounts, digits_compute=dp.get_precision('Account'), string='Balance'),
    }
    _sql_constraints = [
        ('account_live_unique', 'unique (account_id, period_id)', 'Period must be unique per Account !'),
    ]
account_live_line()


class account_live_chart(osv.osv_memory):
    """
    For Chart of Accounts
    """
    _name = "account.live.chart"
    _description = "Account Live Line chart"
    _columns = {
        'fiscalyear': fields.many2one('account.fiscalyear', \
                                    'Fiscal year',  \
                                    help='Keep empty for all open fiscal years'),
        'period_from': fields.many2one('account.period', 'Start period'),
        'period_to': fields.many2one('account.period', 'End period'),
        'target_move': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),
                                        ], 'Target Moves', required=True),
    }

    def _get_fiscalyear(self, cr, uid, context=None):
        """Return default Fiscalyear value"""
        return self.pool.get('account.fiscalyear').find(cr, uid, context=context)

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear_id=False, context=None):
        res = {}
        if fiscalyear_id:
            start_period = end_period = False
            cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               ORDER BY p.date_start ASC, p.special DESC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
            periods =  [i[0] for i in cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            res['value'] = {'period_from': start_period, 'period_to': end_period}
        else:
            res['value'] = {'period_from': False, 'period_to': False}
        return res

    def account_live_chart_open_window(self, cr, uid, ids, context=None):
        """
        Opens chart of Live reports
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of account chart’s IDs
        @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
        """
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        period_obj = self.pool.get('account.period')
        fy_obj = self.pool.get('account.fiscalyear')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context=context)[0]
        result = mod_obj.get_object_reference(cr, uid, 'account_live_report', 'action_account_live_tree')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        fiscalyear_id = data.get('fiscalyear', False) and data['fiscalyear'][0] or False
        result['periods'] = []
        if data['period_from'] and data['period_to']:
            period_from = data.get('period_from', False) and data['period_from'][0] or False
            period_to = data.get('period_to', False) and data['period_to'][0] or False
            result['periods'] = period_obj.build_ctx_periods(cr, uid, period_from, period_to)
        result['context'] = str({'fiscalyear': fiscalyear_id, 'periods': result['periods'], \
                                    'state': data['target_move']})
        if fiscalyear_id:
            result['name'] += ':' + fy_obj.read(cr, uid, [fiscalyear_id], context=context)[0]['code']
        return result

    _defaults = {
        'target_move': 'all',
        'fiscalyear': _get_fiscalyear,
    }

account_live_chart()

