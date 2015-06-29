# -*- coding: utf8 -*-
# live_report.py

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


_SLICE_RANGE = [
    ('period', 'Periodically'),
]


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


class account_live_drange(osv.osv_memory):
    """
    Account Time Slice
    """
    _name        = "account.live.drange"
    _description = "Account Live Time Range"
    _order       = 'date_from'

    def _split_periodically(self, cr, uid, periods, context=None):
        if not context:
            context = {}
        period_obj = self.pool.get('account.period')
        res = []
        for p in period_obj.browse(cr, uid, periods, context=context):
            if not p.special: 
                res.append((p.date_start, p.date_stop))
        return res

    GET_SPLIT = {
        "period": _split_periodically,
    }
    
    _columns = {
        'name': fields.char('Name'),
        'date_from': fields.date('From',required=True),
        'date_to': fields.date('To',required=True),
        'state': fields.char('State',required=True),
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('name',False) == False:
            ds = datetime.strptime(vals['date_from'], '%Y-%m-%d').strftime('%d/%m/%Y')
            de = datetime.strptime(vals['date_to'], '%Y-%m-%d').strftime('%d/%m/%Y')
            vals['name'] = ds + " - " + de
        return super(account_live_drange, self).create(cr, uid, vals, context=context)

    def build_ranges(self, cr, uid, periods, slice_to, state, context):
        drange_list = []
        dates = self.GET_SPLIT.get(slice_to)(self, cr, uid, periods, context=context)
        for c in dates :
            o = {
                'date_from': c[0],
                'date_to': c[1],
                'state': state,                
            }
            drange_list.append(o)
        return [self.create(cr, uid, o, context=context) for o in drange_list]
        
account_live_drange()


class account_live_line(osv.osv_memory):
    """
    Live Account Report line
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
            acc_id = live.account_id.id
            ctx = context.copy()
            # get the move ids for this date range
            ctx.update({                
                'date_from': live.drange_id.date_from,
                'date_to': live.drange_id.date_to,
                'state': live.drange_id.state,
                'chart_account_id': acc_id,
            })
            sums = account_obj.out_compute(
                    cr, 
                    uid, 
                    [acc_id],
                    fields,
                    context=ctx)
            res[live.id] = {n:sums.get(acc_id, False) and sums[acc_id][n] or 0.0 for n in fields}  
        return res
        
        
    def _get_drange(self, cr, uid, ids, names, args, context):
        """retrieve drange infos """
        move_line_obj = self.pool.get('account.move.line')
        if not context:
            context = {}
        res = {}
        for live in self.browse(cr, uid, ids, context=context):
            res[live.id] = {
                'date_from': live.drange_id.date_from,
                'date_to': live.drange_id.date_to,
                'state': live.drange_id.state,
            }  
        return res

    def _get_move_lines2(self, cr, uid, ids, names, args, context):
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
                'date_from': live.drange_id.date_from,
                'date_to': live.drange_id.date_to,
                'state': live.drange_id.state,
                'chart_account_id': live.account_id.id,
            })
            res[live.id] = move_line_obj._query_get(cr, uid, context=ctx)
        return res

    def _get_move_lines(self, cr, uid, ids, name, args, context):
        """retrieve all move lines related to this live period
        and account """
        move_line_obj = self.pool.get('account.move.line')
        if not context:
            context = {}
        res = {}
        for live in self.browse(cr, uid, ids, context=context):
            # get the move ids for this period
            #~ move_line_ids = move_line_obj.search(
            res[live.id] = move_line_obj.search(
                cr, 
                uid,
                [
                    '&', 
                    ('date', '>=', live.drange_id.date_from), 
                    ('date', '<=', live.drange_id.date_to),
                    ('account_id', '=', live.account_id.id) ],
                context=context)
            #~ move_lines = move_line_obj.browse(cr, uid, move_line_ids, context=context)
            # filter out moves that don't include live's account in the
            # transaction
            #~ in_list = []
            #~ for line in move_lines:
                #~ if line.account_id.id == live.account_id.id:
                    #~ if line.move_id.id not in in_list:
                        #~ in_list.append(line.move_id.id)
            #~ res[live.id] = move_line_obj.search(cr, uid,
                                #~ [('move_id', 'in', in_list)],
                                #~ context=context)
        return res
    _columns = {
        "name": fields.char('Name'),
        "account_id": fields.many2one('account.account', 'Account',
                                required=True, ondelete="cascade"),
        "drange_id": fields.many2one('account.live.drange', 'Time Range',
                                required=True, ondelete="cascade"),
        'date_from': fields.function(
                _get_drange,
                type="date",
                string='From',
                multi="drange"),
        'date_to': fields.function(
                _get_drange,
                type="date",
                string='To',
                multi="drange"),
        'state': fields.function(
                _get_drange,
                type="char",
                string='State',
                multi="drange"),
        'credit': fields.float(
                string='Credit',
                digits_compute=dp.get_precision('Account')),
        'debit': fields.float(
                string='Debit',
                digits_compute=dp.get_precision('Account')),
        'balance': fields.float(
                string='Balance',
                digits_compute=dp.get_precision('Account')),
        'move_line_ids': fields.function(
                _get_move_lines, 
                type='one2many',
                relation='account.move.line',
                string="Journal Entries"),
    }

    _sql_constraints = [
        ('live_line_unique',
            'unique (account_id, drange_id)',
            'Account must be unique per Time Range !'),
    ]


    def list_drange(self, cr, uid, context=None):
        ids = self.pool.get('account.live.drange').search(cr,uid,[], context=context)
        result = []
        for drange in self.pool.get('account.live.drange').browse(cr, uid, ids, context=context):
            result.append((drange.id,drange.name))
        return result


account_live_line()


class account_live_chart(osv.osv_memory):
    """
    For Chart of Accounts
    """
    _name = "account.live.chart"
    _description = "Account Live Line chart"

    def _get_fiscalyear(self, cr, uid, context=None):
        """Return default Fiscalyear value"""
        return self.pool.get('account.fiscalyear').find(
                                        cr, uid, context=context)

    _columns = {
        'fiscalyear': fields.many2one('account.fiscalyear',
                                    'Fiscal year',
                                    help='Keep empty for all open fiscal years'),
        'period_from': fields.many2one('account.period', 'Start period'),
        'period_to': fields.many2one('account.period', 'End period'),
        'target_move': fields.selection([('posted', 'All Posted Entries'),
                                         ('all', 'All Entries'),],
                                         'Target Moves', required=True),
        'slices': fields.selection( _SLICE_RANGE, string='Slice...', required=True),
    }

    _defaults = {
        'target_move': 'all',
        'slices': 'period',
        'fiscalyear': _get_fiscalyear,
    }

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear_id=False, 
                                context=None):
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

    def create_live_lines(self, cr, uid, ids, context=None):
        """
        Actually create the lines.
        """
        ctx = context.copy()

        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        live_obj = self.pool.get('account.live.line')
        drange_obj = self.pool.get('account.live.drange')
        periods = []
        data = self.read(cr, uid, ids, [], context=context)[0]
        slice_to = data.get('slices', "period")
        state = data.get('target_move', "all")
        if data['period_from'] and data['period_to']:
            period_from = data.get('period_from', False) and data['period_from'][0] or False
            period_to = data.get('period_to', False) and data['period_to'][0] or False
            periods = period_obj.build_ctx_periods(cr, uid, period_from, period_to)
        account_ids = account_obj.search(cr, uid, [("type","<>","view")])
        accounts = account_obj.browse(cr, uid, account_ids, context=context)
        # first delete all
        to_delete = drange_obj.search(cr, uid, [], context=ctx)
        drange_obj.unlink(cr, uid, to_delete, context=ctx)
        # now create dranges
        drange_ids = drange_obj.build_ranges(cr, uid, periods, slice_to, state, context=context)
        drange = drange_obj.browse(cr, uid, drange_ids, context=context)
        # now create lines
        live_list = []
        for d in drange:
            ctx.update({'date_from': d.date_from, 'date_to':d.date_to})
            sums = account_obj.out_compute(cr, uid, account_ids,
                                            ['debit','credit','balance'],
                                            context=ctx)
            for acc in accounts:
                o = {
                    "name": acc.code + ' for ' + d.name,
                    "account_id": acc.id,
                    "drange_id": d.id,
                    'debit': sums.get(acc.id, False) and sums[acc.id]['debit'] or 0.0,
                    'credit': sums.get(acc.id, False) and sums[acc.id]['credit'] or 0.0,
                    'balance': sums.get(acc.id, False) and sums[acc.id]['balance'] or 0.0,
                }
                live_list.append(o)
        return [live_obj.create(cr, uid, o, context=context) for o in live_list]


account_live_chart()
