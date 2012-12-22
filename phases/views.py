# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Author: Mathijs Dumon
# This work is licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License. 
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/3.0/ or send
# a letter to Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.

import gtk

import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo as FigureCanvasGTK

from generic.views import BaseView, HasChildView, DialogView, NoneView
from generic.views.widgets import ScaleEntry

class EditPhaseView(BaseView, HasChildView):
    title = "Edit Phases"
    builder = "phases/glade/phase.glade"
    top = "edit_phase"
    widget_format = "phase_%s"
    
    csds_view = None    
    csds_view_container = "csds_container"
    
    probabilities_view = None    
    probabilities_view_container = "prob_container"

    components_view = None    
    components_view_container = "comp_container"
           
    def set_csds_view(self, view):
        self.csds_view = view
        if view != None:
            self._add_child_view(view.get_top_widget(), self[self.csds_view_container])
        return view
        
    def set_probabilities_view(self, view):
        self.probabilities_view = view
        if view != None:
            self._add_child_view(view.get_top_widget(), self[self.probabilities_view_container])
        return view
        
    def remove_probabilities(self):
        table =self[self.top]
        table.remove(self["hbox_prob"])
        newtop = table.child_get_property(self["hbox_comp"], "top-attach") - 1
        table.child_set_property(self["hbox_comp"], "top-attach", newtop)
        
    def set_components_view(self, view):
        self.components_view = view
        if view != None:
            self._add_child_view(view.get_top_widget(), self[self.components_view_container])
        return view
    
class EditAtomRatioView(DialogView):
    title = "Edit Atom Ratio"
    subview_builder = "phases/glade/ratio.glade"
    subview_toplevel = "edit_ratio"
    modal = True

    @property    
    def atom1_combo(self):
        return self["ratio_atom1_cmb"]

    @property    
    def atom2_combo(self):
        return self["ratio_atom2_cmb"]
                  
    pass #end of class
    
class EditAtomContentsView(DialogView, HasChildView):
    title = "Edit Atom Contents"
    subview_builder = "phases/glade/contents.glade"
    subview_toplevel = "edit_contents"
    modal = True
    widget_format = "contents_%s"
        
    contents_list_view_container = "container_atom_contents"
      
    def set_contents_list_view(self, view):
        self.contents_list_view = view
        return self._add_child_view(view, self[self.contents_list_view_container])
      
    @property    
    def atom_contents_container(self):
        return self["container_atom_contents"]
                 
    pass #end of class

class EditComponentView(BaseView, HasChildView):
    title = "Edit Component"
    builder = "phases/glade/component.glade"
    top = "edit_component"
    widget_format = "component_%s"

    layer_view = None    
    layer_view_container = "container_layer_atoms"

    interlayer_view = None
    interlayer_view_container = "container_interlayer_atoms"
    
    atom_relations_view = None
    atom_relations_view_container = "container_atom_relations"    

    ucpa_view = None    
    ucpa_view_container = "container_ucp_a"

    ucpb_view = None    
    ucpb_view_container = "container_ucp_b"

        
    def __init__(self, *args, **kwargs):
        BaseView.__init__(self, *args, **kwargs)
        
    def set_layer_view(self, view):
        self.layer_view = view
        return self._add_child_view(view, self[self.layer_view_container])
        
    def set_atom_relations_view(self, view):
        self.atom_relations_view = view
        return self._add_child_view(view, self[self.atom_relations_view_container])
        
    def set_interlayer_view(self, view):
        self.interlayer_view = view
        return self._add_child_view(view, self[self.interlayer_view_container])
        
    def set_ucpa_view(self, view):
        self.ucpa_view = view
        return self._add_child_view(view, self[self.ucpa_view_container])
        
    def set_ucpb_view(self, view):
        self.ucpb_view = view
        return self._add_child_view(view, self[self.ucpb_view_container])
   
class EditUnitCellPropertyView(BaseView):
    builder = "phases/glade/unit_cell_prop.glade"
    top = "box_ucf"
    
class EditCSDSDistributionView(BaseView):
    builder = "phases/glade/csds.glade"
    top = "tbl_csds_distr"
    
    def __init__(self, *args, **kwargs):
        BaseView.__init__(self, *args, **kwargs)
        
        self.graph_parent = self["distr_plot_box"]
        self.setup_matplotlib_widget()
        
    def setup_matplotlib_widget(self):
        style = gtk.Style()
        self.figure = Figure(dpi=72, edgecolor=str(style.bg[2]), facecolor=str(style.bg[2]))
           
        self.plot = self.figure.add_subplot(111)       
        self.figure.subplots_adjust(bottom=0.20)
        
        self.matlib_canvas = FigureCanvasGTK(self.figure)
    
        self.plot.autoscale_view()
    
        self.graph_parent.add(self.matlib_canvas)
        self.graph_parent.show_all()
        
    def update_figure(self, distr_dict):
        self.plot.cla()
        keys, vals = distr_dict.keys(), distr_dict.values()
        #ymax = max(vals)
        self.plot.hist(keys, len(keys), weights=vals, normed=1, ec='b', histtype='stepfilled')
        self.plot.set_ylabel('')
        self.plot.set_xlabel('CSDS', size=14, weight="heavy")
        self.plot.relim()
        self.plot.autoscale_view()
        if self.matlib_canvas != None:
            self.matlib_canvas.draw()
    
    def reset_params(self):
        tbl = self["tbl_params"]
        for child in tbl.get_children():
            tbl.remove(child)
        tbl.resize(1,2)
    
    def add_param_widget(self, label, minimum, maximum):
        tbl = self["tbl_params"]
        rows = tbl.get_property("n-rows") + 1
        tbl.resize(rows, 2)
        
        lbl = gtk.Label(label)
        lbl.set_alignment(1.0,0.5)
        tbl.attach(lbl, 0, 1, rows-1, rows, gtk.FILL, gtk.FILL)
                
        inp = ScaleEntry(minimum, maximum, enforce_range=True)
        tbl.attach(inp, 1, 2, rows-1, rows, gtk.FILL, gtk.FILL)
        
        tbl.show_all()
        
        return inp
    
class AddPhaseView(DialogView):
    title = "Add Phase"
    subview_builder = "phases/glade/addphase.glade"
    subview_toplevel = "add_phase_container"
       
    def __init__(self, *args, **kwargs):
        DialogView.__init__(self, *args, **kwargs)
       
    def get_G(self):
        return int(self["G"].get_value_as_int())
        
    def get_R(self):
        return int(self["R"].get_value_as_int())
        
    def get_phase(self):
        itr = self["cmb_default_phases"].get_active_iter()
        if itr:
            val = self["cmb_default_phases"].get_model().get_value(itr, 1)
            return val if val else None 
        else:
            return None
            
    @property
    def phase_combo_box(self):
        return self["cmb_default_phases"]
        
    pass #end of class
