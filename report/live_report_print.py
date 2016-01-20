# -*- coding: utf-8 -*-

import time
from openerp.report.interface import report_int
import openerp.pooler as pooler
import cStringIO
import csv
class report_csv(report_int):
    def __init__(self, name, table):
        report_int.__init__(self, name)
        self.table = table

    def create(self, cr, uid, ids, datas, context=None):
        """
        Create our CSV
        We format and return the current account.live.line objects
        as a csv document.
        """
        if not context:
            context={}
        self.pool = pooler.get_pool(cr.dbname)
        self._model = self.pool.get(self.table)
        # prepare memory object and csv writer
        fileobj = cStringIO.StringIO()
        fwriter = csv.writer(fileobj, delimiter=',')
        # pool our object and format it how we want.
        data = self._model.map_data(cr, uid, context=context)
        for line in data:
            fwriter.writerow(line)
        final_op = fileobj.getvalue()
        fileobj.close()
        self.title = "Balance Report"
        return final_op, 'csv'
        
report_csv('report.account.live.line.print', 'account.live.line')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
