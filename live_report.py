# -*- coding: utf8 -*-
# live_report.py

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class account_account(osv.osv):
    _inherit = "account.account"
    """
    we need access to the __compute method
    """

    def out_compute(self, cr, uid, ids, field_names, arg=None, context=None,
                      query='', query_params=()):
        return self.__compute( cr, uid, ids, field_names, arg, context,
                              query, query_params)

account_account()


class account_live_line(osv.osv_memory):
    """
    Profit/Loss line
    """
    _name        = "account.live.line"
    _description = "Account Live line"
    _order       = 'account_id'

    def _get_sums(self, cr, uid, ids, names, args, context):
        account_obj = self.pool.get('account.account')
        if not context:
            context = {}
        res = {}
        fields = ['credit', 'debit', 'balance']
        for live in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            # get the move ids for this date range
            ctx.update({                'date_from': live.date_from,
                'date_to': live.date_to,
                'state': live.state,
                'chart_account_id': live.account_id.id,
            })
            sums = account_obj.out_compute(
                    cr, 
                    uid, 
                    [live.account_id.id],
                    fields,
                    context=ctx)
            res[live.id] = {n:sums.get(n) for n in fields}  
        return res
        
        
    def _get_move_lines(self, cr, uid, ids, names, args, context):
        """retrieve all move lines related to this live period
        and account """
        move_line_obj = self.pool.get('account.move.line')
        if not context:
            context = {}
        res = {}
        for live in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            # get the move ids for this date range
            ctx.update({
                'date_from': live.date_from,
                'date_to': live.date_to,
                'state': live.state,
                'chart_account_id': live.account_id.id,
            })
            res[live.id] = move_line_obj._query_get(cr, uid, context=ctx)
        return res

    _columns = {
        "account_id": fields.many2one('account.account', 'Account',
                                required=True, ondelete="cascade"),
        'date_from': fields.date('From',required=True),
        'date_to': fields.date('To',required=True),
        'state': fields.char('State',required=True),
        'credit': fields.function(
                _get_sums,
                type="float",
                digits_compute=dp.get_precision('Account')
                string='Credit',
                multi="sums"),
        'debit': fields.function(
                _get_sums,
                type="float",
                digits_compute=dp.get_precision('Account')
                string='Debit',
                multi="sums"),
        'balance': fields.function(
                _get_sums,
                type="float",
                digits_compute=dp.get_precision('Account')
                string='Balance',
                multi="sums"),
        'move_line_ids': fields.function(
                _get_move_lines, 
                type='one2many',
                relation='account.move.line',
                string="Journal Entries"),
    }


account_live_line()


class account_live_chart(osv.osv_memory):
    """
    For Chart of Accounts
    """
    _name = "account.live.chart"
    _description = "Account Live Line chart"
    _columns = {
        'fiscalyear': fields.many2one('account.fiscalyear',
                                    'Fiscal year',
                                    help='Keep empty for all open fiscal years'),
        'period_from': fields.many2one('account.period', 'Start period'),
        'period_to': fields.many2one('account.period', 'End period'),
        'target_move': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),],
                                         'Target Moves', required=True),
    }

    def _get_fiscalyear(self, cr, uid, context=None):
        """Return default Fiscalyear value"""
        return self.pool.get('account.fiscalyear').find(
                                        cr, uid, context=context)

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

    def _create_live_lines(self, cr, uid, dates, context=None):
        """
        Actually create the lines.
        """
        ctx = context.copy()

        account_obj = self.pool.get('account.account')
        live_obj = self.pool.get('account.live.line')
        account_ids = account_obj.search(cr, uid, [("type","<>","view")])
        # first delete all
        to_delete = live_obj.search(cr, uid, [], context=ctx)
        live_obj.unlink(cr, uid, to_delete, context=ctx)
        # now create
        live_list = []
        for period_id in period_ids:
            ctx.update({'periods': [period_id]})
            sums = account_obj.out_compute(cr, uid, account_ids,
                                            ['debit','credit','balance'],
                                            context=ctx)
            for account_id in account_ids:
                o = {
                    "account_id": account_id,
                    "period_id": period_id,
                    'debit': sums.get(account_id, False) and sums[account_id]['debit'] or 0.0,
                    'credit': sums.get(account_id, False) and sums[account_id]['credit'] or 0.0,
                    'balance': sums.get(account_id, False) and sums[account_id]['balance'] or 0.0,
                }
                if o['credit'] > 0 or o['debit'] > 0 :
                    live_list.append(o)

        return [live_obj.create(cr, uid, o, context=context) for o in live_list]





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

        self._create_live_lines(cr, uid, result['periods'], context=context)

        result['context'] = str({'fiscalyear': fiscalyear_id, 'periods': result['periods'],
                                    'state': data['target_move'],
                                    'search_default_groupby_account': 1})
        if fiscalyear_id:
            result['name'] += ':' + fy_obj.read(cr, uid, [fiscalyear_id], context=context)[0]['code']
        return result

    _defaults = {
        'target_move': 'all',
        'fiscalyear': _get_fiscalyear,
    }

account_live_chart()
