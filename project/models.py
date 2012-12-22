# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Author: Mathijs Dumon
# This work is licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported License. 
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/3.0/ or send
# a letter to Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.

import time

import gtk
from gtkmvc.model import Model, Signal, Observer

import settings

from generic.utils import delayed
from generic.models import ChildModel, DefaultSignal
from generic.models.mixins import ObjectListStoreParentMixin
from generic.models.properties import PropIntel, MultiProperty
from generic.models.treemodels import ObjectListStore, IndexListStore
from generic.io import Storable

from goniometer.models import Goniometer
from specimen.models import Specimen
from mixture.models import Mixture
from phases.models import Phase
from atoms.models import Atom, AtomType

class Project(ChildModel, Storable, ObjectListStoreParentMixin):


    #MODEL INTEL:
    __model_intel__ = [ #TODO add labels
        PropIntel(name="name",                     data_type=str,    storable=True,  has_widget=True),
        PropIntel(name="date",                     data_type=str,    storable=True,  has_widget=True),
        PropIntel(name="description",              data_type=str,    storable=True,  has_widget=True),
        PropIntel(name="author",                   data_type=str,    storable=True,  has_widget=True),
        PropIntel(name="display_marker_angle",     data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="display_calc_color",       data_type=str,    storable=True,  has_widget=True),
        PropIntel(name="display_exp_color",        data_type=str,    storable=True,  has_widget=True),
        PropIntel(name="display_calc_lw",          data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="display_exp_lw",           data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="display_plot_offset",      data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="display_group_by",         data_type=int,    storable=True,  has_widget=True),
        PropIntel(name="display_label_pos",        data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="axes_xscale",              data_type=int,    storable=True,  has_widget=True),
        PropIntel(name="axes_xmin",                data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="axes_xmax",                data_type=float,  storable=True,  has_widget=True),
        PropIntel(name="axes_xstretch",            data_type=bool,   storable=True,  has_widget=True),
        PropIntel(name="axes_yscale",              data_type=int,    storable=True,  has_widget=True),
        PropIntel(name="axes_yvisible",            data_type=bool,   storable=True,  has_widget=True),
        PropIntel(name="goniometer",               data_type=object, storable=True),
        PropIntel(name="specimens",                data_type=object, storable=True,  has_widget=True),
        PropIntel(name="phases",                   data_type=object, storable=True),
        PropIntel(name="mixtures",                 data_type=object, storable=True),
        PropIntel(name="atom_types",               data_type=object, storable=True),
        PropIntel(name="needs_update",             data_type=object, storable=False),           
        PropIntel(name="needs_saving",             data_type=bool,   storable=False),           
    ]
    
    #SIGNALS:
    needs_update = None

    #PROPERTIES:
    name = ""
    date = ""
    description = None
    author = ""
    
    needs_saving = True
    
    _axes_xmin = 0.0
    _axes_xmax = 70.0
    _axes_xstretch = False
    _axes_yvisible = False
    _display_plot_offset = 0.75
    _display_group_by = 1
    _display_marker_angle = 0.0
    _display_label_pos = 0.35
    @Model.getter("axes_xmin", "axes_xmax", "axes_xstretch", "axes_yvisible",
            "display_plot_offset", "display_group_by", "display_marker_angle",
            "display_label_pos")
    def get_axes_value(self, prop_name):
        return getattr(self, "_%s" % prop_name)
    @Model.setter("axes_xmin", "axes_xmax", "axes_xstretch", "axes_yvisible",
            "display_plot_offset", "display_group_by", "display_marker_angle",
            "display_label_pos")
    def set_axes_value(self, prop_name, value):
        if prop_name == "axes_xmin": value = max(value, 0.0)
        if prop_name == "display_group_by": value = max(value, 1)
        setattr(self, "_%s" % prop_name, value)
        self.needs_update.emit()

    def cbb_callback(self, prop_name, value):
        self.needs_update.emit()
    axes_xscale = MultiProperty(0, int, cbb_callback, { 0: "Auto", 1: "Manual" })
    axes_yscale = MultiProperty(0, int, cbb_callback, { 
        0: "Multi normalised",
        1: "Single normalised",
        2: "Unchanged raw counts"
    })
  
    
    _display_calc_color = settings.CALCULATED_COLOR
    _display_exp_color = settings.EXPERIMENTAL_COLOR   
    @Model.getter("display_calc_color", "display_exp_color")
    def get_color(self, prop_name):
        return getattr(self, "_%s" % prop_name)
    @Model.setter("display_calc_color", "display_exp_color")
    def set_color(self, prop_name, value):
        if value != getattr(self, "_%s" % prop_name):
            setattr(self, "_%s" % prop_name, value)
            calc = ("calc" in prop_name)
            if self.specimens:
                for specimen in self.specimens.iter_objects():
                    if calc and specimen.inherit_calc_color:
                        specimen.calculated_pattern.color = value
                    elif not calc and specimen.inherit_exp_color:
                        specimen.experimental_pattern.color = value
            self.needs_update.emit()

    _display_calc_lw = settings.CALCULATED_LINEWIDTH
    _display_exp_lw = settings.EXPERIMENTAL_LINEWIDTH   
    @Model.getter("display_calc_lw", "display_exp_lw")
    def get_lw(self, prop_name):
        return getattr(self, "_%s" % prop_name)
    @Model.setter("display_calc_lw", "display_exp_lw")
    def set_lw(self, prop_name, value):
        if value != getattr(self, "_%s" % prop_name):
            setattr(self, "_%s" % prop_name, float(value))
            calc = ("calc" in prop_name)
            if self.specimens:
                for specimen in self.specimens.iter_objects():
                    if calc and specimen.inherit_calc_lw:
                        specimen.calculated_pattern.lw = value
                    elif not calc and specimen.inherit_exp_lw:
                        specimen.experimental_pattern.lw = value
            self.needs_update.emit()

    
    _specimens = None
    def get_specimens_value(self): return self._specimens
    
    _phases = None
    def get_phases_value(self): return self._phases
    
    _atom_types = None
    def get_atom_types_value(self): return self._atom_types
    
    _mixtures = None
    def get_mixtures_value(self): return self._mixtures
    
    goniometer = None
           
    # ------------------------------------------------------------
    #      Initialisation and other internals
    # ------------------------------------------------------------
    def __init__(self, name = "Project name", date = time.strftime("%d/%m/%Y"),
            description = "Project description", author = "Project author",
            goniometer = None, atom_types = None, phases = None, 
            specimens = None, mixtures = None,
            display_marker_angle=None, display_plot_offset=None, display_group_by=None,
            display_calc_color=None, display_exp_color=None, display_label_pos=None,
            display_calc_lw=None, display_exp_lw=None,
            axes_xscale=None, axes_xmin=None, axes_xmax=None, 
            axes_xstretch=None, axes_yscale=None, axes_yvisible=None,
            load_default_data=True, **kwargs):
        ChildModel.__init__(self, parent=kwargs.get("parent", None))
        self.parent = kwargs.get("parent") #FIXME??? old project files seem to have an issue here?
        Storable.__init__(self)
        
        self.before_needs_update_lock = False
        self.needs_update = DefaultSignal(before=self.before_needs_update)

        self.display_marker_angle = display_marker_angle or self.display_marker_angle
        self.display_calc_color = display_calc_color or self.display_calc_color
        self.display_exp_color = display_exp_color or self.display_exp_color
        self.display_calc_lw = display_calc_lw or self.display_calc_lw
        self.display_exp_lw = display_exp_lw or self.display_exp_lw
        self.display_plot_offset = display_plot_offset or self.display_plot_offset
        self.display_group_by = display_group_by or self.display_group_by
        self.display_label_pos = display_label_pos or self.display_label_pos
        
        self.axes_xscale = axes_xscale or self.axes_xscale
        self.axes_xmin = axes_xmin or self.axes_xmin
        self.axes_xmax = axes_xmax or self.axes_xmax
        self.axes_xstretch = axes_xstretch or self.axes_xstretch
        self.axes_yscale = axes_yscale or self.axes_yscale
        self.axes_yvisible = axes_yvisible or self.axes_yvisible

        atom_types = atom_types or self.get_depr(kwargs, None, "data_atom_types")
        phases = phases or self.get_depr(kwargs, None, "data_phases")
        specimens = specimens or self.get_depr(kwargs, None, "data_specimens")
        mixtures = mixtures or self.get_depr(kwargs, None, "data_mixtures")
        self._atom_types = self.parse_liststore_arg(atom_types, IndexListStore, AtomType)        
        self._phases = self.parse_liststore_arg(phases, ObjectListStore, Phase)
        self._specimens = self.parse_liststore_arg(specimens, ObjectListStore, Specimen)
        self._mixtures = self.parse_liststore_arg(mixtures, ObjectListStore, Mixture)

        for phase in self._phases._model_data:
            phase.resolve_json_references()
            self.observe_model(phase)            
        for specimen in self._specimens.iter_objects():
            self.observe_model(specimen)

        self._atom_types.connect("item-removed", self.on_atom_type_item_removed)        
        self._phases.connect("item-removed", self.on_phase_item_removed)
        self._specimens.connect("item-removed", self.on_specimen_item_removed)
        self._mixtures.connect("item-removed", self.on_mixture_item_removed)
        
        self._atom_types.connect("item-inserted", self.on_atom_type_item_inserted)
        self._phases.connect("item-inserted", self.on_phase_item_inserted)
        self._specimens.connect("item-inserted", self.on_specimen_item_inserted)
        self._mixtures.connect("item-inserted", self.on_mixture_item_inserted)
        
        self.description = gtk.TextBuffer()
        
        self.name = str(name or self.get_depr(kwargs, "", "data_name"))
        self.date = str(date or self.get_depr(kwargs, "", "data_date"))
        self.description.set_text(str(description or self.get_depr(kwargs, "", "data_description")))
        self.author = str(author or self.get_depr(kwargs, "", "data_author"))
        
        self.goniometer = self.parse_init_arg(
            goniometer or self.get_depr(kwargs, None, "data_goniometer"), 
            Goniometer(parent=self), child=True)       

        if load_default_data and not settings.VIEW_MODE and \
            len(self._atom_types._model_data)==0: self.load_default_data()
            
        self.needs_saving = True
        
    def load_default_data(self):
        AtomType.get_from_csv(
            settings.get_def_file("ATOM_SCAT_FACTORS"), self.atom_types.append)
            
    # ------------------------------------------------------------
    #      Notifications of observable properties
    # ------------------------------------------------------------
    def on_phase_item_inserted(self, model, item, *data):
        if item.parent != self: item.parent = self
        self.observe_model(item)
    def on_atom_type_item_inserted(self, model, item, *data):
        if item.parent != self: item.parent = self
    def on_specimen_item_inserted(self, model, item, *data):
        if item.parent != self: item.parent = self
        self.observe_model(item)
    def on_mixture_item_inserted(self, model, item, *data):
        if item.parent != self: item.parent = self

    def on_phase_item_removed(self, model, item, *data):
        if item.based_on != None:
            item.based_on = None
        for phase in self._phases._model_data:
            if phase.based_on == item:
                phase.based_on = None
        for mixture in self.mixtures.iter_objects():
            mixture.unset_phase(item)
        if not self.before_needs_update_lock:
            self.needs_update.emit() #propagate signal
    def on_atom_type_item_removed(self, model, item, *data):
        if not self.before_needs_update_lock:
            self.needs_update.emit() #propagate signal
    def on_specimen_item_removed(self, model, item, *data):
        self.relieve_model(item)
        for mixture in self.mixtures.iter_objects():
            mixture.unset_specimen(item)
        if not self.before_needs_update_lock:
            self.needs_update.emit() #propagate signal
    def on_mixture_item_removed(self, model, item, *data):
        pass

    @Observer.observe("needs_update", signal=True)
    def notify_needs_update(self, model, prop_name, info):
        self.needs_saving = True
        if not self.before_needs_update_lock:
            self.needs_update.emit() #propagate signal

    @delayed("before_needs_update_lock")
    def before_needs_update(self, after):
        if not self.before_needs_update_lock:
            self.before_needs_update_lock = True
            t1 = time.time()
            for mixture in self.mixtures.iter_objects():
                mixture.apply_result()
            t2 = time.time()
            print '%s took %0.3f ms' % ("before_needs_update", (t2-t1)*1000.0)
            after()
            self.before_needs_update_lock = False

    def freeze_updates(self):
        self.before_needs_update_lock = True

    def thaw_updates(self):
        self.before_needs_update_lock = False

    # ------------------------------------------------------------
    #      Input/Output stuff
    # ------------------------------------------------------------
    @classmethod
    def from_json(type, **kwargs):
        project = type(**kwargs)
        project.needs_saving = False #don't mark this when just loaded
        return project
                
    def save_object(self, filename):
        #if filename.endswith(".pyxrd"):
        Storable.save_object(self, filename)
        #elif filename.endswith(".zpd"):
        #TODO
        self.needs_saving = False
    
    # ------------------------------------------------------------
    #      Methods & Functions
    # ------------------------------------------------------------ 
    def get_scale_factor(self, specimen):
        """
        Get the factor with which to scale raw data and the scaled offset
                
        :rtype: tuple containing the scale factor and the (scaled) offset
        """
        if self.axes_yscale == 0:
            return (1.0 / (self.get_max_intensity() or 1.0), self.display_offset)
        elif self.axes_yscale == 1:
            return (1.0 / (specimen.max_intensity or 1.0), self.display_offset)
        elif self.axes_yscale == 2:
            return (1.0, self.display_offset * self.get_max_intensity())
        else:
            raise ValueError, "Wrong value for 'axes_yscale' in %s: %d; should be 0, 1 or 2" % (self, yscale)
   
    def get_max_intensity(self):
        max_intensity = 0
        print self.parent
        if self.parent != None:
            for specimen in self.parent.current_specimens:
                max_intensity = max(specimen.max_intensity, max_intensity)
        return max_intensity

    pass #end of class
    
    
    

