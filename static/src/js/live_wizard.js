openerp.account_live_report = function (instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web.account_live_report = instance.web.account_live_report || {};

    instance.web.views.add('tree_live', 'instance.web.account_live_report.LiveListView');
    instance.web.account_live_report.LiveListView = instance.web.ListView.extend({
        init: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.current_account = null;
            this.current_drange = null;
            this.default_account = null;
            this.default_drange = null;
        },
        start: function() {
            var tmp = this._super.apply(this, arguments);
            var self = this;
            var defs = [];
            this.$el.parent().prepend(QWeb.render("LiveLaunchWizard", {widget: this}));
            this.$el.parent().find(".oe_live_launch_wizard").click(function() {
                self.run_wizard();
            });
            this.$el.parent().find(".oe_live_print").click(function() {
                self.print_report();
            });
            this.$el.parent().find('.oe_live_select_drange').change(function() {
                self.current_drange = this.value === '' ? null : parseInt(this.value);
                self.do_search(self.last_domain, self.last_context, self.last_group_by);
            });
            var mod = new instance.web.Model("account.live.line", self.dataset.context, self.dataset.domain);
            defs.push(mod.call("list_drange", []).then(function(result) {
                self.drange = result;
            }));
            return $.when(tmp, defs);
        },
        do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(this._super, this);
            var o;
            self.$el.parent().find('.oe_live_select_drange').children().remove().end();
            self.$el.parent().find('.oe_live_select_drange').append(new Option('', ''));
            for (var i = 0;i < self.drange.length;i++){
                o = new Option(self.drange[i][1], self.drange[i][0]);
                self.$el.parent().find('.oe_live_select_drange').append(o);
            }    
            self.$el.parent().find('.oe_live_select_drange').val(self.current_drange).attr('selected',true);
            return self.search_by_account_drange();
        },
        search_by_account_drange: function() {
            var self = this;
            var domain = [];
            if (self.current_drange !== null) domain.push(["drange_id", "=", self.current_drange]);
            self.last_context["drange_id"] = self.current_drange === null ? false : self.current_drange;
            var compound_domain = new instance.web.CompoundDomain(self.last_domain, domain);
            self.dataset.domain = compound_domain.eval();
            return self.old_search(compound_domain, self.last_context, self.last_group_by);
        },
        run_wizard: function() {
            var self = this;
            var mod = new instance.web.Model("account.live.line", self.dataset.context, self.dataset.domain);
            new instance.web.Model("ir.model.data").call("get_object_reference", ["account_live_report", "action_account_live_chart"]).then(function(result) {
                var additional_context = _.extend({
                    active_model: self.model
                });
                return self.rpc("/web/action/load", {
                    action_id: result[1],
                    context: additional_context
                }).done(function (result) {
                    result.context = instance.web.pyeval.eval('contexts', [result.context, additional_context]);
                    result.flags = result.flags || {};
                    result.flags.new_window = true;
                    return self.do_action(result, {
                        on_close: function () {
                            mod.call("list_drange", []).then(function(result) {
                                self.drange = result;
                                self.current_drange = '';
                                self.$el.parent().find('.oe_live_select_drange').val('').change();
                            });
                        }
                    });
                });
            });
        },
        print_report: function(){
            var self = this;
            return self.rpc("/web/report", {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.live.line.print',
                'datas': {
                        'model': 'account.live.line',
                        'ids': false,
                        'ids': false,
                        'report_type': 'txt'
                    },
                'nodestroy': true,
            });
        },
    });

};
