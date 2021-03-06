# -*- coding: utf8 -*-
# live_report.py

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import pooler
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

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
            ctx = dict(context or {}, account_period_prefer_normal=True)
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
            ctx = dict(context or {}, account_period_prefer_normal=True)
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

    
    def compute_data(self, cr, uid, ids, context=None):
        ctx = dict(context or {}, account_period_prefer_normal=True)
        account_obj = self.pool.get('account.account')
        period_obj = self.pool.get('account.period')
        drange_obj = self.pool.get('account.live.drange')
        periods = []
        slice_to = ctx.get('slices', "period")
        state = ctx.get('target_move', "all")
        if ctx.get('period_from', False) and ctx.get('period_to', False):
            period_from = context['period_from']
            period_to = context['period_to']
            periods = period_obj.build_ctx_periods(cr, uid, period_from, period_to)
        account_ids = account_obj.search(cr, uid, [("type","<>","view")])
        accounts = account_obj.browse(cr, uid, account_ids, context=ctx)
        # first delete all
        to_delete = drange_obj.search(cr, uid, [], context=ctx)
        drange_obj.unlink(cr, uid, to_delete, context=ctx)
        # now create dranges
        drange_ids = drange_obj.build_ranges(cr, uid, periods, slice_to, state, context=ctx)
        drange = drange_obj.browse(cr, uid, drange_ids, context=ctx)
        # now create lines
        # we need to exclude accounts that have 0 balance in all dranges
        live_list = []
        exclude_dic = {}
        for d in drange:
            ctx.update({'date_from': d.date_from, 'date_to':d.date_to})
            sums = account_obj.out_compute(cr, uid, account_ids,
                                            ['debit','credit','balance'],
                                            context=ctx)
            for acc in accounts:
                if not exclude_dic.get(acc.id):
                    exclude_dic[acc.id] = []
                o = {
                    "name": acc.name + ' for ' + d.name,
                    "account_id": acc.id,
                    "drange_id": d.id,
                    'debit': sums.get(acc.id, False) and sums[acc.id]['debit'] or 0.0,
                    'credit': sums.get(acc.id, False) and sums[acc.id]['credit'] or 0.0,
                    'balance': sums.get(acc.id, False) and sums[acc.id]['balance'] or 0.0,
                }
                if o['balance'] > 0.0 : #this goes in for sure
                    live_list.append(o)
                else:
                    exclude_dic[acc.id].append(o)
        for l in exclude_dic.values():
            if len(l) < len(drange): #at least 1 element has a value
                live_list.extend(l)
        for o in live_list:
            self.create(cr, uid, o, context=ctx)
        return True


    def map_data(self, cr, uid, context=None):
        if not context:
            context = {}
        data = []
        #build headers
        headers = ['Code','Account']
        dranges = self.list_drange(cr, uid, context)
        headers.extend([i[1] for i in dranges])
        headers.append('Total')

        pos = [i[0] for i in dranges]
        
        data.append(headers)
        # build flattened lines
        ids = self.search(cr,uid,[], context=context)
        lines = []
        line_drange = {}
        line_codes = {}
        for line in self.browse(cr, uid, ids, context=context):
            
            if not line_drange.get(line.account_id.code):
                line_drange[line.account_id.code] = {}
                lines.append((line.account_id.code, line.account_id.name))
            # we need to put them in the right order. That's the challenge
            line_drange[line.account_id.code][line.drange_id.id] = line.balance
        for k in line_drange.keys(): #that would be the account code...
            line_codes[k] = [line_drange[k][p] for p in pos]
        
        
        for l in lines:
            a = []
            a.extend(l)
            a.extend(line_codes.get(l[0]))
            a.append(sum(line_codes.get(l[0])))
            data.append(a)
        
        return data
    
    def print_report(self, cr, uid, ids, context=None):
        if context.get('recompute'):
            self.compute_data(cr, uid, ids, context=context)
            
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.live.line.print',
            'datas': {
                    'model': 'account.live.line',
                    'id': ids and ids[0] or False,
                    'ids': ids and ids or [],
                    'report_type': 'csv'
                },
            'nodestroy': True
        }

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
        ctx = dict(context or {}, account_period_prefer_normal=True)
        pool_obj = pooler.get_pool(cr.dbname)
        live_obj = pool_obj.get('account.live.line')
        
        ctx.update({
            'fiscalyear': self.browse(cr, uid, ids)[0].fiscalyear.id,
            'period_from': self.browse(cr, uid, ids)[0].period_from.id,
            'period_to': self.browse(cr, uid, ids)[0].period_to.id,
            'target_move': self.browse(cr, uid, ids)[0].target_move,
            'slices': self.browse(cr, uid, ids)[0].slices,
            })

        return live_obj.compute_data(cr, uid, ids, context=ctx)

account_live_chart()


class account_live_print(osv.osv_memory):
    """
    For Chart of Accounts
    """
    _name = "account.live.csv"
    _description = "Print Live CSV table"

    _columns = {
        'recompute': fields.boolean('Recompute before ?'),
    }
    _defaults = {
        'recompute': lambda *a: False,
    }

    def print_report(self, cr, uid, ids, context=None):
        ctx = dict(context or {}, account_period_prefer_normal=True)
        pool_obj = pooler.get_pool(cr.dbname)
        live_obj = pool_obj.get('account.live.line')

        ctx.update({
            'recompute': self.browse(cr, uid, ids)[0].recompute,
            })

        return live_obj.print_report(cr, uid, ids, context=ctx)

         


account_live_print()
